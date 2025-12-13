import React, { useState } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "react-native";

import RootNavigation from "./navigation/rootNavigation";
import LoginScreen from "./Login/LoginScreen";
import Signup from "./Login/Signup";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { WebSocketProvider } from "./Driving/context/WebSocketContext";

function Gate() {
  const { isLoggedIn, login } = useAuth();
  const [authRoute, setAuthRoute] = useState("login"); // 'login' | 'signup'

  if (isLoggedIn) return <RootNavigation />;

  return authRoute === "login" ? (
    <LoginScreen
      onLoginSuccess={login}
      onGoSignup={() => setAuthRoute("signup")}
    />
  ) : (
    <Signup onGoLogin={() => setAuthRoute("login")} />
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <StatusBar barStyle="dark-content" />
      <WebSocketProvider>
        <AuthProvider>
          <Gate />
        </AuthProvider>
      </WebSocketProvider>
    </SafeAreaProvider>
  );
}
