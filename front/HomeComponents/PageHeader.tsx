import { View,Text,StyleSheet } from "react-native";


export const PageHeader = () => {
  return (
    <View style={styles.Pagecontainer}>
      <Text style={styles.Pagetitle}>{"운전의 정석"}</Text>
    </View>
  );
};


const styles = StyleSheet.create({
  Pagecontainer: {
    paddingVertical: 15,
    paddingHorizontal: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
    alignItems: 'center',
    justifyContent: 'center',
  },
  Pagetitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1a237e', // 짙은 파란색 계열
  },
});