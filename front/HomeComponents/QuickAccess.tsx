import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons'; // 아이콘 import

export const QuickAccess = () => {
  const navigation = useNavigation();

  // 네비게이션 매핑
  const routes = ["주행", "기록실", "설정", "마이페이지"];

  // 아이콘 매핑
  const icons: (keyof typeof Ionicons.glyphMap)[] = [
    "car-sport-outline",  // 주행 시작
    "time-outline",       // 기록 조회
    "settings-outline",   // 환경 설정
    "person-outline"      // 마이페이지
  ];

  return (
    <View style={quickAccessStyles.container}>
      <Text style={quickAccessStyles.title}>빠른 기능</Text>
      <View style={quickAccessStyles.grid}>
        {['주행 시작', '기록 조회', '환경 설정', '마이페이지'].map((item, index) => (
          <TouchableOpacity
            key={index}
            style={quickAccessStyles.gridItem}
            onPress={() => navigation.navigate(routes[index] as never)}
          >
            <View
              style={[
                quickAccessStyles.iconBox,
                { backgroundColor: ['#3478F6', '#34C759', '#9D5BD9', '#6366F1'][index] },
              ]}
            >
              <Ionicons name={icons[index]} size={22} color="white" />
            </View>
            <Text style={quickAccessStyles.itemText}>{item}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
};

const quickAccessStyles = StyleSheet.create({
  container: { marginHorizontal: 16, marginBottom: 20 },
  title: { fontSize: 16, fontWeight: 'bold', marginBottom: 10 },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  gridItem: {
    width: '48%',
    backgroundColor: 'white',
    borderRadius: 15,
    padding: 15,
    alignItems: 'flex-start',
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 3,
  },
  iconBox: {
    width: 50,
    height: 50,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 25, // 원형으로 변경
    marginBottom: 10,
  },
  itemText: { fontSize: 14, fontWeight: '500' },
});
