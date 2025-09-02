import React, { useState } from "react";
import { Star } from "lucide-react";

const StarRating = ({ messageId, currentRating, onRate }) => {
  const [rating, setRating] = useState(currentRating || 0);
  const [hoveredRating, setHoveredRating] = useState(0);

  const handleRate = async (value) => {
    setRating(value);
    await onRate(messageId, value);
  };

  return (
    <div className="flex items-center gap-1 mt-2">
      <span className="text-xs text-gray-500 mr-1">Rate response:</span>
      {[1, 2, 3, 4, 5].map((value) => (
        <button
          key={value}
          type="button"
          onClick={() => handleRate(value)}
          onMouseEnter={() => setHoveredRating(value)}
          onMouseLeave={() => setHoveredRating(0)}
          className="transition-all hover:scale-110"
        >
          <Star
            size={16}
            className={`${
              value <= (hoveredRating || rating)
                ? "fill-yellow-400 text-yellow-400"
                : "text-gray-300"
            } transition-colors`}
          />
        </button>
      ))}
      {rating > 0 && (
        <span className="text-xs text-gray-500 ml-1">({rating}/5)</span>
      )}
    </div>
  );
};

export default StarRating;
