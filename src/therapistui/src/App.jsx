import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Homepage from "./pages/Homepage";
import LoginPage from "./pages/LoginPage";
import SignUpPage from "./pages/SignUpPage";
import { useAuthStore } from "./store/useAuthStore";
import { Toaster } from "react-hot-toast";

const App = () => {
  const { authUser, checkAuth, isCheckingAuth } = useAuthStore();

  return (
    <div>
      <Navbar></Navbar>
      <Routes>
        <Route path="/" element={authUser ? <Homepage /> : <LoginPage />} />
        <Route
          path="/signup"
          element={!authUser ? <SignUpPage /> : <Homepage />}
        />
        <Route path="/login" element={<LoginPage />} />
      </Routes>
      <Toaster />
    </div>
  );
};

export default App;
