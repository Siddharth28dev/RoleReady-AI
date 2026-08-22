// App.jsx
// Paper: "5-stage workflow guides candidates through career preparation"

import { useState } from "react";
import { AppProvider, useApp } from "./context/AppContext";
import Login          from "./pages/Login";
import Register       from "./pages/Register";
import ResumeUpload   from "./pages/ResumeUpload";
import RoleSelection  from "./pages/RoleSelection";
import Interview      from "./pages/Interview";
import Feedback       from "./pages/Feedback";
import TodoList       from "./pages/TodoList";
import StageBar       from "./components/StageBar";

function AuthGate() {
  const [mode, setMode] = useState("login"); // "login" | "register"
  return mode === "login"
    ? <Login onSwitchToRegister={() => setMode("register")} />
    : <Register onSwitchToLogin={() => setMode("login")} />;
}

function WorkflowRouter() {
  const { currentStage } = useApp();
  return (
    <>
      <StageBar />
      {currentStage === 1 && <ResumeUpload />}
      {currentStage === 2 && <RoleSelection />}
      {currentStage === 3 && <Interview />}
      {currentStage === 4 && <Feedback />}
      {currentStage === 5 && <TodoList />}
    </>
  );
}

function Root() {
  const { token, user, logout } = useApp();

  if (!token || !user) {
    return <AuthGate />;
  }

  return (
    <>
      <div className="topbar">
        <span>Signed in as {user.name}</span>
        <button className="link-btn" onClick={logout}>Log out</button>
      </div>
      <WorkflowRouter />
    </>
  );
}

export default function App() {
  return (
    <AppProvider>
      <div className="app">
        <Root />
      </div>
    </AppProvider>
  );
}