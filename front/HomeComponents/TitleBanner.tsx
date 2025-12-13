import { View, Text, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";

export const TitleBanner = () => (
  <View style={headerStyles.container}>
    <View>
      <Text style={headerStyles.mainText}>완벽한 운전을 시작하세요</Text>
      <Text style={headerStyles.subText}>AI가 실시간으로 운전을 도와드립니다</Text>
    </View>
    <View style={headerStyles.iconBox}>
      <Ionicons name="car-sport-outline" size={30} color="white" />
    </View>
  </View>
);



const headerStyles = StyleSheet.create({
  container: {
    backgroundColor: '#3478F6',
    borderRadius: 15,
    padding: 20,
    marginHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  mainText: { fontSize: 18, fontWeight: 'bold', color: 'white' },
  subText: { fontSize: 14, color: '#E0E0E0', marginTop: 5 },
  iconBox: {
    width: 50,
    height: 50,
    backgroundColor: '#3478F6', // 배경과 같은 색
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 10,
  },
});