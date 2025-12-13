// LoginScreen.jsx
import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  ActivityIndicator,
  Alert,
} from "react-native";

import AsyncStorage from "@react-native-async-storage/async-storage";
const SERVER_BASE = "http://15.165.244.204:8080";
const BLUE = "#2357EB";

export default function LoginScreen({ onLoginSuccess, onGoSignup }) {
  const [id, setId] = useState("");
  const [password, setPassword] = useState("");
  const [focus, setFocus] = useState(null);
  const [loading, setLoading] = useState(false);

const handleLogin = async () => {
  if (!id.trim() || !password.trim()) {
    Alert.alert("로그인 실패", "아이디와 비밀번호를 모두 입력하세요.");
    return;
  }

  setLoading(true);

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10000);

  try {
    const res = await fetch(`${SERVER_BASE}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        loginId: id.trim(),
        password: password,
      }),
      signal: controller.signal,
    });

    clearTimeout(timer);
    const raw = await res.clone().text();
    console.log("로그인 응답 raw:", raw);
    console.log("로그인 응답 status:", res.status);

    if (raw.includes('"code":404') || raw.includes('"code":400') || raw.includes('"code":401')) {
      let msg = "아이디 또는 비밀번호가 올바르지 않습니다.";
      try {
        const errJson = await res.json();
        if (errJson?.message) msg = errJson.message;
      } catch (_) {}
      throw new Error(msg);
    }

    const data = await res.json();
    console.log("로그인 응답 데이터:", data);

    // ✅ 토큰 저장
    const token = data?.data?.accessToken;
    if (token) {
      await AsyncStorage.setItem("accessToken", token);
      console.log("✅ accessToken 저장 완료:", token);
    } else {
      console.warn("⚠️ accessToken이 응답에 없습니다.");
    }

    onLoginSuccess?.(data);
  } catch (e) {
    const aborted = e?.name === "AbortError";
    Alert.alert(
      "로그인 실패",
      aborted ? "네트워크 지연으로 로그인에 실패했습니다. 다시 시도해 주세요." : String(e.message || e)
    );
  } finally {
    setLoading(false);
  }
};
  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: "#F5F7FB" }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {/* 상단 아이콘/타이틀 */}
        <View style={styles.hero}>
          <View style={styles.heroIcon}>
            <Text style={styles.carEmoji}>🚗</Text>
          </View>
          <Text style={styles.title}>운전의 정석</Text>
          <Text style={styles.subtitle}>안전하고 완벽한 드라이빙의 시작</Text>
        </View>

        {/* 입력 폼 */}
        <View style={styles.form}>
          <Text style={styles.label}>
            아이디 <Text style={styles.required}>*</Text>
          </Text>
          <TextInput
            style={[styles.input, focus === "id" && styles.inputFocused]}
            placeholder="아이디를 입력하세요"
            placeholderTextColor="#A8B0BF"
            value={id}
            onChangeText={setId}
            onFocus={() => setFocus("id")}
            onBlur={() => setFocus(null)}
            autoCapitalize="none"
            editable={!loading}
          />

          <Text style={[styles.label, { marginTop: 18 }]}>
            비밀번호 <Text style={styles.required}>*</Text>
          </Text>
          <TextInput
            style={[styles.input, focus === "pw" && styles.inputFocused]}
            placeholder="비밀번호를 입력하세요"
            placeholderTextColor="#A8B0BF"
            value={password}
            onChangeText={setPassword}
            onFocus={() => setFocus("pw")}
            onBlur={() => setFocus(null)}
            secureTextEntry
            editable={!loading}
          />

          <TouchableOpacity
            style={[styles.loginBtn, loading && { opacity: 0.7 }]}
            onPress={handleLogin}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#FFF" />
            ) : (
              <Text style={styles.loginBtnText}>로그인</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity style={styles.signUpBtn} onPress={onGoSignup} disabled={loading}>
            <Text style={styles.signUpBtnText}>회원가입</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.footer}>AI와 함께하는 완벽한 운전 솔루션</Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 20,
    paddingTop: 36,
    paddingBottom: 24,
    minHeight: "100%",
  },
  hero: { alignItems: "center", marginBottom: 28 },
  heroIcon: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: "#E9F0FF",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 16,
  },
  carEmoji: { fontSize: 36 },
  title: { fontSize: 28, fontWeight: "800", color: "#0F172A" },
  subtitle: { marginTop: 6, fontSize: 14, color: "#64748B" },
  form: { marginTop: 14 },
  label: { fontSize: 14, color: "#374151", marginBottom: 8, fontWeight: "600" },
  required: { color: "#EF4444" },
  input: {
    width: "100%",
    height: 52,
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: "#E2E8F0",
    paddingHorizontal: 14,
  },
  inputFocused: {
    borderColor: "#2F62F1",
    shadowColor: "#2F62F1",
    shadowOpacity: 0.12,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  loginBtn: {
    marginTop: 24,
    height: 56,
    backgroundColor: BLUE,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  loginBtnText: { color: "#FFF", fontSize: 18, fontWeight: "700" },
  signUpBtn: {
    marginTop: 12,
    height: 56,
    backgroundColor: "#FFFFFF",
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1.5,
    borderColor: BLUE,
  },
  signUpBtnText: { color: BLUE, fontSize: 16, fontWeight: "700" },
  footer: { textAlign: "center", color: "#8A93A3", marginTop: 36 },
});
