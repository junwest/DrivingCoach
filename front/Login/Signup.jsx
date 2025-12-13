// Signup.jsx
import React, { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ScrollView, Modal, Alert, ActivityIndicator,
} from "react-native";
import DateTimePicker from "@react-native-community/datetimepicker";

const SERVER_BASE = "http://15.165.244.204:8080";
const BLUE = "#2357EB";
const R = 12;

// 아이디 규칙(백엔드 4~20자 힌트 반영)
const validLoginId = (s) => /^[a-zA-Z0-9_\-]{4,20}$/.test(s || "");

export default function Signup({ onGoLogin }) {
  const [nickname, setNickname] = useState("");
  const [gender, setGender] = useState("M");
  const [birth, setBirth] = useState(null);
  const [showPicker, setShowPicker] = useState(false);

  const [loginId, setLoginId] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");

  // 중복 체크 상태: idle | checking | ok | taken
  const [idCheck, setIdCheck] = useState("idle");
  const [idCheckMsg, setIdCheckMsg] = useState("");

  const fmt = (d) =>
    !d
      ? "년 - 월 - 일"
      : `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
          d.getDate()
        ).padStart(2, "0")}`;

  // 아이디 입력이 바뀌면 중복확인 다시 요구
  const onChangeLoginId = (v) => {
    setLoginId(v);
    if (idCheck !== "idle") {
      setIdCheck("idle");
      setIdCheckMsg("");
    }
  };

  const checkDuplicated = async () => {
    const id = loginId.trim();
    if (!validLoginId(id)) {
      Alert.alert("확인", "아이디는 4~20자, 영문/숫자/밑줄/하이픈만 가능합니다.");
      return;
    }

    setIdCheck("checking");
    setIdCheckMsg("");

    try {
      const res = await fetch(`${SERVER_BASE}/api/auth/duplicated`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ loginId: id }),
      });

      const raw = await res.clone().text();
       console.log("중복확인 raw:", raw);

      let json = null;
      try { json = JSON.parse(raw); } catch {}

      // 백엔드 응답형을 방어적으로 해석
      const msg = json?.message || raw || "";
      let isTaken = false;

      if (json?.data?.duplicated !== undefined) {
        isTaken = !!json.data.duplicated;
      } else if (json?.duplicated !== undefined) {
        isTaken = !!json.duplicated;
      } else if (typeof json?.data === "boolean") {
        isTaken = json.data;
      } else if (/중복|exist|이미|사용.*불가|사용할 수 없습니다/i.test(msg)) {
        isTaken = true;
      }

      if (!res.ok) {
        setIdCheck("idle");
        setIdCheckMsg(msg || "중복 확인 실패");
        Alert.alert("중복 확인 실패", msg || "잠시 후 다시 시도해 주세요.");
        return;
      }

      if (isTaken) {
        setIdCheck("taken");
        setIdCheckMsg("이미 사용 중인 아이디입니다.");
      } else {
        setIdCheck("ok");
        setIdCheckMsg("사용 가능한 아이디입니다.");
      }
    } catch (e) {
      setIdCheck("idle");
      setIdCheckMsg("네트워크 오류로 중복 확인에 실패했습니다.");
      Alert.alert("오류", "네트워크 문제로 중복 확인에 실패했습니다.");
    }
  };

  const submit = async () => {
  if (!nickname.trim()) return Alert.alert("확인", "닉네임을 입력해 주세요.");
  if (!birth) return Alert.alert("확인", "생년월일을 선택해 주세요.");
  if (!validLoginId(loginId)) return Alert.alert("확인", "아이디 형식을 다시 확인해 주세요.");
  if (idCheck !== "ok")
    return Alert.alert("확인", "아이디 중복확인을 완료해 주세요.");
  if (pw.length < 6) return Alert.alert("확인", "비밀번호는 6자 이상으로 설정해 주세요.");
  if (pw !== pw2) return Alert.alert("확인", "비밀번호 확인이 일치하지 않습니다.");

  const birthDate = fmt(birth); // ex: "2001-01-01"
  const genderApi = gender === "M" ? "MALE" : "FEMALE";

  try {
    const res = await fetch(`${SERVER_BASE}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        nickname,
        gender: genderApi,
        birthDate,
        loginId,
        password: pw,
      }),
    });

    const raw = await res.clone().text();
    console.log("회원가입 raw:", raw);

    const json = await res.json();

    if (!res.ok || json?.code >= 400) {
      Alert.alert("회원가입 실패", json?.message || "서버 오류가 발생했습니다.");
      return;
    }

    Alert.alert("회원가입 완료", "로그인 화면으로 이동합니다.", [
      { text: "확인", onPress: () => onGoLogin?.() },
    ]);
  } catch (e) {
    console.error(e);
    Alert.alert("오류", "회원가입에 실패했습니다. 다시 시도해 주세요.");
  }
};

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: "#F6F8FB" }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      {/* 상단 헤더 */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onGoLogin} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
          <Text style={styles.backArrow}>‹</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>회원가입</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        {/* 닉네임 */}
        <Text style={styles.label}>닉네임 <Text style={styles.required}>*</Text></Text>
        <TextInput
          style={styles.input}
          placeholder="닉네임을 입력하세요"
          placeholderTextColor="#A8B0BF"
          value={nickname}
          onChangeText={setNickname}
        />

        {/* 성별 */}
        <Text style={[styles.label, { marginTop: 16 }]}>성별 <Text style={styles.required}>*</Text></Text>
        <View style={styles.segmentRow}>
          <TouchableOpacity onPress={() => setGender("M")} style={[styles.segment, gender==="M" && styles.segmentActive]}>
            <Text style={[styles.segmentText, gender==="M" && styles.segmentTextActive]}>남성</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => setGender("F")} style={[styles.segment, gender==="F" && styles.segmentActive]}>
            <Text style={[styles.segmentText, gender==="F" && styles.segmentTextActive]}>여성</Text>
          </TouchableOpacity>
        </View>

        {/* 생년월일 */}
        <Text style={[styles.label, { marginTop: 16 }]}>생년월일 <Text style={styles.required}>*</Text></Text>
        <TouchableOpacity style={styles.inputWithIcon} onPress={() => setShowPicker(true)}>
          <Text style={[styles.inputText, !birth && { color: "#A8B0BF" }]}>{fmt(birth)}</Text>
          <Text style={styles.calendarIcon}>📅</Text>
        </TouchableOpacity>

        {/* 아이디 + 중복확인 */}
        <Text style={[styles.label, { marginTop: 16 }]}>아이디 <Text style={styles.required}>*</Text></Text>
        <View style={styles.row}>
          <TextInput
            style={[styles.input, { flex: 1, marginRight: 8 }]}
            placeholder="아이디를 입력하세요 (4~20자)"
            placeholderTextColor="#A8B0BF"
            value={loginId}
            onChangeText={onChangeLoginId}
            autoCapitalize="none"
          />
          <TouchableOpacity
            style={[styles.checkBtn, idCheck === "checking" && { opacity: 0.7 }]}
            onPress={checkDuplicated}
            disabled={idCheck === "checking"}
          >
            {idCheck === "checking" ? (
              <ActivityIndicator color="#FFF" />
            ) : (
              <Text style={styles.checkBtnText}>중복확인</Text>
            )}
          </TouchableOpacity>
        </View>
        {!!idCheckMsg && (
          <Text
            style={[
              styles.helper,
              idCheck === "ok" ? { color: "#059669" } : { color: "#DC2626" },
            ]}
          >
            {idCheckMsg}
          </Text>
        )}

        {/* 비밀번호 */}
        <Text style={[styles.label, { marginTop: 16 }]}>비밀번호 <Text style={styles.required}>*</Text></Text>
        <TextInput
          style={styles.input}
          placeholder="비밀번호를 입력하세요"
          placeholderTextColor="#A8B0BF"
          value={pw}
          onChangeText={setPw}
          secureTextEntry
        />

        <Text style={[styles.label, { marginTop: 16 }]}>비밀번호 확인 <Text style={styles.required}>*</Text></Text>
        <TextInput
          style={styles.input}
          placeholder="비밀번호를 다시 입력하세요"
          placeholderTextColor="#A8B0BF"
          value={pw2}
          onChangeText={setPw2}
          secureTextEntry
        />

        {/* 가입 버튼(중복확인 통과해야 활성화) */}
        <TouchableOpacity
          style={[styles.submitBtn, idCheck !== "ok" && { opacity: 0.5 }]}
          onPress={submit}
          disabled={idCheck !== "ok"}
        >
          <Text style={styles.submitText}>회원가입</Text>
        </TouchableOpacity>

        <View style={{ height: 20 }} />
      </ScrollView>

      {/* DatePicker */}
      {Platform.OS === "android" ? (
        showPicker && (
          <DateTimePicker
            mode="date"
            display="calendar"
            value={birth || new Date(2000, 0, 1)}
            onChange={(_, date) => { setShowPicker(false); if (date) setBirth(date); }}
            maximumDate={new Date()}
          />
        )
      ) : (
        <Modal visible={showPicker} transparent animationType="fade">
          <View style={styles.modalBackdrop}>
            <View style={styles.modalSheet}>
              <DateTimePicker
                mode="date"
                display="spinner"
                value={birth || new Date(2000, 0, 1)}
                onChange={(_, date) => date && setBirth(date)}
                maximumDate={new Date()}
                style={{ alignSelf: "stretch" }}
              />
              <TouchableOpacity style={styles.modalDone} onPress={() => setShowPicker(false)}>
                <Text style={styles.modalDoneText}>완료</Text>
              </TouchableOpacity>
            </View>
          </View>
        </Modal>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  header: {
    height: 54, flexDirection: "row", alignItems: "center",
    paddingHorizontal: 12, backgroundColor: "#FFFFFF",
    borderBottomWidth: 1, borderBottomColor: "#EEF2F7",
  },
  backArrow: { fontSize: 28, color: "#111827", width: 24 },
  headerTitle: { flex: 1, textAlign: "center", fontSize: 18, fontWeight: "800", color: "#111827" },

  container: { padding: 16 },
  label: { fontSize: 14, color: "#374151", marginBottom: 8, fontWeight: "600" },
  required: { color: "#EF4444" },

  input: {
    height: 52, backgroundColor: "#FFFFFF", borderRadius: R,
    borderWidth: 1.5, borderColor: "#E2E8F0", paddingHorizontal: 14,
  },
  inputWithIcon: {
    height: 52, backgroundColor: "#FFFFFF", borderRadius: R,
    borderWidth: 1.5, borderColor: "#E2E8F0", paddingHorizontal: 14,
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
  },
  inputText: { fontSize: 16, color: "#111827" },
  calendarIcon: { fontSize: 18 },

  segmentRow: { flexDirection: "row", gap: 12 },
  segment: {
    flex: 1, height: 48, backgroundColor: "#FFFFFF",
    borderWidth: 1.5, borderColor: "#E2E8F0", borderRadius: R,
    alignItems: "center", justifyContent: "center",
  },
  segmentActive: { backgroundColor: "#2563EB", borderColor: "#2563EB" },
  segmentText: { fontSize: 16, color: "#111827", fontWeight: "700" },
  segmentTextActive: { color: "#FFFFFF" },

  row: { flexDirection: "row", alignItems: "center" },
  checkBtn: {
    height: 52, paddingHorizontal: 14, backgroundColor: BLUE,
    borderRadius: 10, alignItems: "center", justifyContent: "center",
  },
  checkBtnText: { color: "#FFFFFF", fontSize: 14, fontWeight: "700" },
  helper: { marginTop: 6, fontSize: 12 },

  submitBtn: {
    marginTop: 22, height: 56, backgroundColor: BLUE,
    borderRadius: 14, alignItems: "center", justifyContent: "center",
  },
  submitText: { color: "#FFFFFF", fontSize: 18, fontWeight: "700" },

  modalBackdrop: {
    flex: 1, backgroundColor: "rgba(0,0,0,0.35)",
    alignItems: "center", justifyContent: "flex-end",
  },
  modalSheet: {
    width: "100%", backgroundColor: "#FFFFFF",
    borderTopLeftRadius: 16, borderTopRightRadius: 16,
    paddingTop: 8, paddingBottom: 12,
  },
  modalDone: { alignSelf: "stretch", marginTop: 6, alignItems: "center", paddingVertical: 12 },
  modalDoneText: { fontSize: 16, fontWeight: "700", color: BLUE },
});
