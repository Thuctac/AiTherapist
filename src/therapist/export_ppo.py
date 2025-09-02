import os, json, time, argparse
from typing import Optional
from sqlalchemy import create_engine, text as sql_text
from sqlalchemy.exc import OperationalError

def env(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(key, default)

def get_engine(url: Optional[str]):
    db_url = url or env("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL environment variable must be set (or pass --db-url).")
    echo_sql = bool(int(env("SQL_ECHO", "0")))
    return create_engine(db_url, echo=echo_sql, future=True)

def wait_for_db(engine, tries: int = 10, sleep_s: float = 2.0) -> None:
    for _ in range(tries):
        try:
            with engine.connect() as conn:
                conn.execute(sql_text("SELECT 1"))
            return
        except OperationalError:
            print("[export_ppo] waiting for database …"); time.sleep(sleep_s)
    raise RuntimeError(f"Could not connect to the database after {tries} tries")

def map_label_weight(r: float, min_pos: float, max_neg: float, keep_neutral: bool, downweight_pos: float):
    if r is None: return None, 0.0
    if r >= min_pos:
        w = min(1.0, (r - 3.0) / 2.0) * max(0.0, min(1.0, float(downweight_pos)))
        return 1, max(w, 0.05)
    if r <= max_neg:
        w = min(1.0, (3.0 - r) / 2.0)
        return 0, max(w, 0.05)
    return (1, 0.1) if keep_neutral else (None, 0.0)

def build_prompt(text_rep: str, audio_rep: str, image_rep: str) -> str:
    return (
        "<system>\n"
        "Role: Responsive Multimodal Therapist\n"
        "Goal: Engage naturally with the user's immediate response and guide therapeutic conversation through authentic dialogue, "
        "integrating insights from multimodal analysis while maintaining focus on what the user just shared.\n"
        "Backstory: You are an experienced therapist who believes in meeting people where they are. You listen carefully to each response "
        "and build on what the person just shared, rather than following a script. You integrate insights from text, image, and audio analysis "
        "seamlessly into natural conversation. Your strength lies in recognizing the specific emotional moment the person is in and responding "
        "authentically to that exact moment, helping them explore their thoughts and feelings through genuine dialogue rather than therapeutic templates.\n\n"
        "Conversation Task:\n"
        "0. Consider the full conversation history as context, but give priority to the user’s most recent message.\n"
        "   IMPORTANT: Don't repeat advice already given in the conversation history.\n"
        "1. READ the user's message. Wait until you receive the reports of the textTherapist, imageTherapist, voiceTherapist.\n"
        "   If it's a simple greeting, social chat, or casual conversation → respond naturally and briefly.\n"
        "   If it contains a 'how to' or steps request → give concrete steps immediately (no generic validation first).\n"
        "2. ANALYZE the three reports:\n"
        "   - If user shared an image: reference what it shows and how it reflects their emotional state\n"
        "   - If user shared voice: reference tone, pace, or emotional indicators\n"
        "   - Cross-reference insights across modalities\n"
        "3. If reports show negative patterns → add gentle cognitive reframing\n"
        "   If not → respond supportively\n"
        "4. End with one follow-up question\n"
        "CRITICAL: Only reference media if actually shared. Never invent.\n"
        "</system>\n"
        "<user>\n"
        f"TEXT REPORT:\n{(text_rep or '').strip()}\n\n"
        f"VOICE REPORT:\n{(audio_rep or '').strip()}\n\n"
        f"IMAGE REPORT:\n{(image_rep or '').strip()}\n"
        "</user>\n"
        "<assistant>"
    )

def run_export(out_path: str, db_url: Optional[str] = None) -> None:
    engine = get_engine(db_url)
    wait_for_db(engine)

    min_pos        = float(env("PPO_MIN_POS", "4.0"))
    max_neg        = float(env("PPO_MAX_NEG", "2.0"))
    keep_neutral   = bool(int(env("PPO_KEEP_NEUTRAL", "0")))
    downweight_pos = float(env("PPO_DOWNWEIGHT_POS", "1.0"))

    # Pick the latest rating per message (by ratings.id), only unexported bot replies.
    select_sql = sql_text("""
        SELECT DISTINCT ON (m.id)
            m.id              AS message_id,
            m.text_report     AS text_report,
            m.audio_report    AS audio_report,
            m.image_report    AS image_report,
            m.bot_text        AS bot_text,
            m.timestamp       AS created_at,
            r.rating::float   AS rating
        FROM messages m
        JOIN ratings r ON r.message_id = m.id
        WHERE m.exported = FALSE
          AND m.bot_text IS NOT NULL
        ORDER BY m.id, r.id DESC
    """)

    with engine.connect() as conn:
        rows = conn.execute(select_sql).mappings().all()

    if not rows:
        print("No unexported rated bot messages found. Nothing to export."); return

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    n_pos = n_neg = n_drop = 0
    exported_ids = []

    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            completion = (r["bot_text"] or "").strip()
            if not completion:
                continue

            rating = float(r["rating"]) if r["rating"] is not None else None
            label, weight = map_label_weight(rating, min_pos, max_neg, keep_neutral, downweight_pos)
            if label is None:
                n_drop += 1
                continue

            prompt = build_prompt(r["text_report"], r["audio_report"], r["image_report"])

            rec = {
                "prompt": prompt,
                "completion": completion,  
                "label": int(label),
                "weight": round(float(weight), 3),
                "meta": {
                    "message_id": r["message_id"],
                    "created_at": str(r["created_at"]),
                    "rating": round(rating, 3) if rating is not None else None,
                },
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            exported_ids.append(r["message_id"])
            if label == 1: n_pos += 1
            else: n_neg += 1

    print(f"✅ Wrote {out_path}")
    print(f"   positives: {n_pos} | negatives: {n_neg} | dropped(neutral): {n_drop}")
    print(f"   marking exported=true for {len(exported_ids)} messages …")

    if exported_ids:
        # Mark exported to avoid reusing data next time
        placeholders = ", ".join([f"({i})" for i in exported_ids])
        update_sql = sql_text(f"""
            UPDATE messages
            SET exported = TRUE
            WHERE id IN (SELECT x.id FROM (VALUES {placeholders}) AS x(id))
        """)
        with engine.begin() as conn:
            conn.execute(update_sql)

    print("✅ Done. Future exports will skip already-exported messages.")

def parse_args():
    p = argparse.ArgumentParser(description="Export PPO dataset from Postgres (incremental, single rating).")
    p.add_argument("--out", default="ppo.jsonl", help="Output JSONL path")
    p.add_argument("--db-url", default=None, help="Override DB URL (else use DATABASE_URL env)")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    run_export(args.out, args.db_url)
