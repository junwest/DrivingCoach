import React, { useState, useEffect } from "react";
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  ActivityIndicator, Alert, Modal, TextInput, KeyboardAvoidingView, Platform
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { PageHeaderD } from "../../MyPageScreenComponents/pageHeaderD";
import { useAuth } from "../../auth/AuthContext";
import AsyncStorage from "@react-native-async-storage/async-storage";
import DateTimePicker from "@react-native-community/datetimepicker"; // 날짜 선택용

const SERVER_BASE = "http://15.165.244.204:8080";
const BLUE = "#2357EB";
const RED = "#DC2626";

// --- API 호출 헬퍼 ---
const api = async (path, method = "GET", body = null) => {
  try {
    const token = await AsyncStorage.getItem("accessToken");
    if (!token) return null;

    const res = await fetch(`${SERVER_BASE}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: body ? JSON.stringify(body) : null,
    });

    const text = await res.text();
    try {
      const json = JSON.parse(text);
      return { ok: res.ok, status: res.status, data: json };
    } catch {
      return { ok: res.ok, status: res.status, data: null }; // 응답 본문 없을 때
    }
  } catch (e) {
    console.error("API Error:", e);
    return { ok: false, status: 0, error: e };
  }
};

// --- 날짜 포맷 (yyyy-mm-dd) ---
const fmtDate = (d) => {
  if (!d) return "";
  const date = new Date(d);
  return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
};

export default function MyPageScreen() {
  const { logout } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  // 모달 상태
  const [modalType, setModalType] = useState(null); // 'checkPw' | 'updateInfo' | 'changePw' | null
  const [nextAction, setNextAction] = useState(null); // 비밀번호 확인 후 실행할 동작

  // 입력 필드들
  const [passwordInput, setPasswordInput] = useState(""); // 확인용 비번
  const [newPassword, setNewPassword] = useState("");
  const [newPassword2, setNewPassword2] = useState("");

  // 정보 수정용
  const [editNickname, setEditNickname] = useState("");
  const [editGender, setEditGender] = useState("");
  const [editBirth, setEditBirth] = useState(new Date());
  const [showDatePicker, setShowDatePicker] = useState(false);


  // --- 1. 프로필 조회 ---
  const loadProfile = async () => {
    setLoading(true);
    const res = await api("/api/users/me");
    if (res && res.ok && res.data.success) {
      setProfile(res.data.data);
    }
    setLoading(false);
  };

  useEffect(() => { loadProfile(); }, []);

  // --- 2. 비밀번호 확인 (공통 절차) ---
  const handleCheckPassword = async () => {
    if (!passwordInput) return Alert.alert("알림", "비밀번호를 입력해주세요.");

    const res = await api("/api/mypage/passwordCheck", "POST", { password: passwordInput });
    
    if (res && res.ok && res.data?.data?.check) {
      setPasswordInput("");
      setModalType(null); // 비번 확인창 닫고
      
      // 다음 단계 진행
      if (nextAction === "updateInfo") {
        // 정보 수정 모달 열기 전 데이터 초기화
        setEditNickname(profile?.nickname || "");
        setEditGender(profile?.gender === "MALE" ? "M" : "F");
        setEditBirth(profile?.birthDate ? new Date(profile.birthDate) : new Date());
        setModalType("updateInfo");
      } else if (nextAction === "changePw") {
        setModalType("changePw");
      } else if (nextAction === "deleteAccount") {
        handleDeleteAccount(); // 바로 삭제 진행
      }
    } else {
      Alert.alert("오류", "비밀번호가 일치하지 않습니다.");
    }
  };

  // --- 3. 회원정보 수정 ---
  const handleUpdateInfo = async () => {
    const body = {
      nickname: editNickname,
      gender: editGender === "M" ? "MALE" : "FEMALE",
      birthDate: fmtDate(editBirth),
    };

    const res = await api("/api/mypage/infoupdate", "POST", body);
    if (res && res.ok) {
      Alert.alert("성공", "회원정보가 수정되었습니다.");
      setModalType(null);
      loadProfile(); // 프로필 갱신
    } else {
      Alert.alert("실패", res?.data?.message || "수정에 실패했습니다.");
    }
  };

  // --- 4. 비밀번호 변경 ---
  const handleChangePw = async () => {
    if (newPassword.length < 8) return Alert.alert("알림", "비밀번호는 8자 이상이어야 합니다.");
    if (newPassword !== newPassword2) return Alert.alert("알림", "비밀번호 확인이 일치하지 않습니다.");

    // (주의) API 문서에는 현재 비번과 새 비번을 같이 보내라고 되어 있을 수 있으니 확인 필요.
    // 여기서는 'passwordCheck'를 이미 통과했으므로, 'api/mypage/passwordChange'는 새 비번만 받을 수도 있고,
    // 혹은 'api/users/me/password' (ChangePasswordRequest)를 쓴다면 old, new 둘 다 필요할 수 있습니다.
    // **백엔드 코드(SettingController, MyPageController) 참고 결과:**
    // MyPageController -> /api/mypage/passwordChange (ChangePasswordRequest: currentPassword, newPassword)
    // 따라서 currentPassword를 다시 입력받거나, 아까 입력한 값을 저장해둬야 합니다.
    // **보안상 비번 확인 단계에서 입력한 값을 잠시 가지고 있다가 보내는 방식으로 구현합니다.**
    
    // (수정: handleCheckPassword에서 비번 확인용으로만 쓰고 초기화해버렸으니,
    // 변경 API 호출 시에는 '현재 비번'을 다시 입력받거나, 
    // 비번 변경 화면에서 '현재 비번', '새 비번', '새 비번 확인' 3개를 다 받는 게 정석입니다.)
    
    // 여기서는 편의상 '비밀번호 변경' 모달에서 '현재 비번'도 같이 입력받도록 UI를 수정하겠습니다.
    // -> 아래 UI 코드 참고
  };
  
  const requestChangePw = async (currentPw, newPw) => {
      const res = await api("/api/mypage/passwordChange", "POST", {
          currentPassword: currentPw,
          newPassword: newPw
      });
      
      if(res && res.ok) {
          Alert.alert("성공", "비밀번호가 변경되었습니다. 다시 로그인해주세요.");
          logout();
      } else {
          Alert.alert("실패", res?.data?.message || "변경 실패");
      }
  }


  // --- 5. 계정 삭제 ---
  const handleDeleteAccount = async () => {
    Alert.alert("경고", "정말로 계정을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.", [
      { text: "취소", style: "cancel" },
      {
        text: "삭제", style: "destructive", onPress: async () => {
          const res = await api("/api/auth/delete", "POST");
          if (res && res.ok) {
            Alert.alert("알림", "계정이 삭제되었습니다.");
            logout();
          } else {
            Alert.alert("오류", "계정 삭제 실패");
          }
        }
      }
    ]);
  };

  // --- 렌더링 헬퍼 ---
  const formatTime = (seconds) => {
      if (!seconds) return "0분";
      const h = Math.floor(seconds / 3600);
      const m = Math.floor((seconds % 3600) / 60);
      return h > 0 ? `${h}시간 ${m}분` : `${m}분`;
  };
  
  // --- [모달] 비밀번호 확인 ---
  const renderCheckPwModal = () => (
    <Modal transparent visible={modalType === 'checkPw'} animationType="fade">
      <KeyboardAvoidingView behavior={Platform.OS==="ios"?"padding":undefined} style={styles.modalOverlay}>
        <View style={styles.modalCard}>
          <Text style={styles.modalTitle}>비밀번호 확인</Text>
          <Text style={styles.modalSub}>안전한 정보 접근을 위해 비밀번호를 입력해주세요.</Text>
          
          <TextInput
            style={styles.input}
            placeholder="비밀번호"
            secureTextEntry
            value={passwordInput}
            onChangeText={setPasswordInput}
          />
          
          <View style={styles.modalBtns}>
            <TouchableOpacity style={styles.btnCancel} onPress={() => setModalType(null)}>
              <Text style={styles.btnTextGray}>취소</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.btnConfirm} onPress={handleCheckPassword}>
              <Text style={styles.btnTextWhite}>확인</Text>
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );

  // --- [모달] 정보 수정 ---
  const renderUpdateInfoModal = () => (
    <Modal visible={modalType === 'updateInfo'} animationType="slide">
      <SafeAreaView style={{flex:1}}>
        <View style={styles.fullModalHeader}>
            <TouchableOpacity onPress={() => setModalType(null)}>
                <Text style={styles.headerBtn}>취소</Text>
            </TouchableOpacity>
            <Text style={styles.headerTitle}>정보 수정</Text>
            <TouchableOpacity onPress={handleUpdateInfo}>
                <Text style={[styles.headerBtn, {color:BLUE}]}>저장</Text>
            </TouchableOpacity>
        </View>
        
        <ScrollView style={{padding:20}}>
            <Text style={styles.label}>닉네임</Text>
            <TextInput style={styles.input} value={editNickname} onChangeText={setEditNickname} />
            
            <Text style={[styles.label, {marginTop:20}]}>성별</Text>
            <View style={styles.genderRow}>
                <TouchableOpacity 
                    style={[styles.genderBtn, editGender==="M" && styles.genderBtnActive]}
                    onPress={()=>setEditGender("M")}>
                    <Text style={[styles.genderText, editGender==="M" && {color:"white"}]}>남성</Text>
                </TouchableOpacity>
                <TouchableOpacity 
                    style={[styles.genderBtn, editGender==="F" && styles.genderBtnActive]}
                    onPress={()=>setEditGender("F")}>
                    <Text style={[styles.genderText, editGender==="F" && {color:"white"}]}>여성</Text>
                </TouchableOpacity>
            </View>

            <Text style={[styles.label, {marginTop:20}]}>생년월일</Text>
            <TouchableOpacity style={styles.input} onPress={()=>setShowDatePicker(true)}>
                <Text>{fmtDate(editBirth)}</Text>
            </TouchableOpacity>
            
            {showDatePicker && (
                <DateTimePicker
                    value={editBirth}
                    mode="date"
                    display="spinner"
                    onChange={(e, date) => {
                        setShowDatePicker(false);
                        if(date) setEditBirth(date);
                    }}
                />
            )}
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );

  // --- [모달] 비밀번호 변경 (현재비번 + 새비번 입력) ---
  const [currPwForChange, setCurrPwForChange] = useState("");
  
  const renderChangePwModal = () => (
    <Modal visible={modalType === 'changePw'} animationType="slide">
      <SafeAreaView style={{flex:1}}>
         <View style={styles.fullModalHeader}>
            <TouchableOpacity onPress={() => setModalType(null)}>
                <Text style={styles.headerBtn}>취소</Text>
            </TouchableOpacity>
            <Text style={styles.headerTitle}>비밀번호 변경</Text>
            <View style={{width:40}}/> 
        </View>
        
        <View style={{padding:20}}>
            <Text style={styles.label}>현재 비밀번호</Text>
            <TextInput style={styles.input} secureTextEntry value={currPwForChange} onChangeText={setCurrPwForChange} />

            <Text style={[styles.label, {marginTop:20}]}>새 비밀번호</Text>
            <TextInput style={styles.input} secureTextEntry value={newPassword} onChangeText={setNewPassword} placeholder="8자 이상 입력" />

            <Text style={[styles.label, {marginTop:20}]}>새 비밀번호 확인</Text>
            <TextInput style={styles.input} secureTextEntry value={newPassword2} onChangeText={setNewPassword2} />
            
            <TouchableOpacity 
                style={[styles.confirmBtn, {marginTop:30}]}
                onPress={() => {
                    if (newPassword !== newPassword2) return Alert.alert("오류", "새 비밀번호가 일치하지 않습니다.");
                    requestChangePw(currPwForChange, newPassword);
                }}
            >
                <Text style={styles.btnTextWhite}>변경하기</Text>
            </TouchableOpacity>
        </View>
      </SafeAreaView>
    </Modal>
  );


  // 메인 화면 렌더링
  return (
    <SafeAreaView style={{ flex: 1 }} edges={["top", "left", "right"]}>
      <View style={styles.container}>
        <PageHeaderD />
        
        <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 80 }}>
          {!loading && profile ? (
            <>
            {/* 프로필 카드 */}
            <View style={styles.card}>
                <Text style={styles.cardTitle}>마이페이지</Text>
                <View style={styles.profileBox}>
                    <View style={styles.avatar} />
                    <View>
                        <Text style={styles.name}>{profile.nickname}</Text>
                        <Text style={styles.subMuted}>@{profile.loginId}</Text>
                    </View>
                </View>
                <View style={styles.statRow}>
                    <View style={styles.statItem}>
                        <Text style={styles.statMain}>{profile.totalDrivingCount}회</Text>
                        <Text style={styles.subMuted}>총 주행</Text>
                    </View>
                    <View style={styles.dividerY} />
                    <View style={styles.statItem}>
                        <Text style={styles.statMain}>{formatTime(profile.totalDrivingTime)}</Text>
                        <Text style={styles.subMuted}>누적 시간</Text>
                    </View>
                </View>
            </View>

            {/* 안전 점수 */}
            <View style={styles.card}>
                <Text style={styles.cardTitle}>안전 점수</Text>
                <View style={styles.progressBar}>
                     <View style={[styles.progressFill, { width: `${Math.min(profile.safeScore, 100)}%` }]} />
                </View>
                <Text style={{textAlign:'right', marginTop:8, fontWeight:'bold'}}>{profile.safeScore}점</Text>
            </View>
            
            {/* 회원 정보 */}
            <View style={styles.card}>
                <Text style={styles.cardTitle}>회원 정보</Text>
                <InfoRow label="성별" value={profile.gender === "MALE" ? "남성" : "여성"} />
                <InfoRow label="생년월일" value={profile.birthDate} />
                <InfoRow label="가입일" value={profile.createdAt?.slice(0,10)} />
            </View>

            {/* 계정 관리 */}
             <View style={styles.card}>
              <Text style={styles.cardTitle}>계정 관리</Text>
              
              <MenuButton text="회원정보 수정" onPress={() => {
                  setNextAction("updateInfo");
                  setModalType("checkPw"); // 비번 확인 먼저
              }} />
              
              <MenuButton text="비밀번호 변경" onPress={() => {
                   setCurrPwForChange(""); setNewPassword(""); setNewPassword2("");
                   setModalType("changePw"); // 비번 변경 모달 바로 열기 (안에서 현재 비번 입력받음)
              }} />
              
              <MenuButton text="계정 삭제" color={RED} onPress={() => {
                  setNextAction("deleteAccount");
                  setModalType("checkPw"); // 비번 확인 먼저
              }} />
            </View>

            <TouchableOpacity style={styles.logoutBtn} onPress={logout}>
                <Text style={styles.logoutText}>로그아웃</Text>
            </TouchableOpacity>
            </>
          ) : (
              <ActivityIndicator size="large" style={{marginTop:50}} />
          )}
        </ScrollView>
      </View>
      
      {/* 모달들 */}
      {renderCheckPwModal()}
      {renderUpdateInfoModal()}
      {renderChangePwModal()}
      
    </SafeAreaView>
  );
}

// --- 하위 컴포넌트 ---
const InfoRow = ({label, value}) => (
    <View style={{flexDirection:'row', justifyContent:'space-between', paddingVertical:12, borderBottomWidth:1, borderColor:'#F1F5F9'}}>
        <Text style={{color:'#111827'}}>{label}</Text>
        <Text style={{color:'#6B7280'}}>{value}</Text>
    </View>
);

const MenuButton = ({text, color="#111827", onPress}) => (
    <TouchableOpacity onPress={onPress} style={{flexDirection:'row', justifyContent:'space-between', paddingVertical:14, borderBottomWidth:1, borderColor:'#F1F5F9'}}>
        <Text style={{color, fontSize:14}}>{text}</Text>
        <Text style={{color:'#9CA3AF'}}>›</Text>
    </TouchableOpacity>
);


const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F2F4F7" },
  card: { backgroundColor: "#FFF", borderRadius: 12, padding: 16, marginBottom: 14 },
  cardTitle: { fontSize: 16, fontWeight: "700", marginBottom: 12 },
  
  profileBox: { flexDirection: 'row', alignItems: 'center', marginBottom: 15 },
  avatar: { width: 50, height: 50, borderRadius: 25, backgroundColor: '#E5E7EB', marginRight: 12 },
  name: { fontSize: 18, fontWeight: '600' },
  subMuted: { fontSize: 12, color: '#6B7280' },
  
  statRow: { flexDirection: 'row', backgroundColor: '#F8FAFC', borderRadius: 8, padding: 10 },
  statItem: { flex: 1, alignItems: 'center' },
  statMain: { fontWeight: '700', fontSize: 16 },
  dividerY: { width: 1, backgroundColor: '#E5E7EB' },
  
  progressBar: { height: 10, backgroundColor: '#E5E7EB', borderRadius: 5, overflow:'hidden' },
  progressFill: { height: '100%', backgroundColor: '#10B981' },
  
  logoutBtn: { backgroundColor: RED, padding: 15, borderRadius: 10, alignItems: 'center', marginTop: 10 },
  logoutText: { color: 'white', fontWeight: '700' },

  // 모달 스타일
  modalOverlay: { flex:1, backgroundColor:'rgba(0,0,0,0.5)', justifyContent:'center', padding:20 },
  modalCard: { backgroundColor:'white', borderRadius:16, padding:24 },
  modalTitle: { fontSize:18, fontWeight:'bold', marginBottom:8 },
  modalSub: { color:'#666', marginBottom:16 },
  input: { borderWidth:1, borderColor:'#E2E8F0', borderRadius:8, padding:12, fontSize:16 },
  modalBtns: { flexDirection:'row', marginTop:20, gap:10 },
  btnCancel: { flex:1, padding:12, backgroundColor:'#F1F5F9', borderRadius:8, alignItems:'center' },
  btnConfirm: { flex:1, padding:12, backgroundColor: BLUE, borderRadius:8, alignItems:'center' },
  btnTextGray: { color:'#333', fontWeight:'600' },
  btnTextWhite: { color:'white', fontWeight:'600' },
  
  fullModalHeader: { flexDirection:'row', justifyContent:'space-between', alignItems:'center', padding:16, borderBottomWidth:1, borderColor:'#eee' },
  headerTitle: { fontSize:18, fontWeight:'bold' },
  headerBtn: { fontSize:16, color:'#666' },
  label: { fontSize:14, fontWeight:'600', marginBottom:8, color:'#333' },
  
  genderRow: { flexDirection:'row', gap:10 },
  genderBtn: { flex:1, padding:12, borderWidth:1, borderColor:'#eee', borderRadius:8, alignItems:'center' },
  genderBtnActive: { backgroundColor: BLUE, borderColor: BLUE },
  genderText: { fontSize:16, color:'#333' },
  
  confirmBtn: { backgroundColor: BLUE, padding:15, borderRadius:10, alignItems:'center' }
});