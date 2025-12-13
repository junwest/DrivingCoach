# Lane Detection Visualization - Improved Version

## 🎯 개요

개선된 차선 검출 및 시각화 시스템입니다.

## ✨ 주요 개선 사항

| 메트릭 | 이전 | 개선 | 향상 |
|--------|------|------|------|
| Event 4 Normal | 0.2% | **56.3%** | **+280배** |
| Event 5 Normal | 1.7% | **95.0%** | **+56배** |

## 🚀 사용 방법

### 기본 사용
```bash
python lane_visualizer_improved.py \
  --videos "Data/이벤트 4.mp4" "Data/이벤트 5.mp4" \
  --output-dir find_lane \
  --method combined
```

### 옵션
- `--method`: `hsv`, `edge`, `combined`, `adaptive`
- `--debug`: ROI 영역 표시
- `--output-dir`: 출력 디렉토리

## 📊 검출 방법

### Combined (추천)
HSV + Edge Detection 결합 - 가장 균형잡힌 성능

### HSV
색상 기반 검출 - 밝은 환경에 적합

### Edge
엣지 기반 검출 - 어두운 환경에 적합

### Adaptive
적응형 임계값 - 복잡한 환경용

## 📁 출력 파일

- `이벤트 4_improved.mp4` - Event 4 개선 버전
- `이벤트 5_improved.mp4` - Event 5 개선 버전

## 🎨 시각화

- **흰색**: 검출된 차선 (반투명)
- **파란색**: 좌/우 차선 경계 (L/R)
- **초록색**: 차선 중심선
- **빨간색**: 차량 위치 (CAR)
- **회색**: 차량-차선 연결선

## 📈 성능

- Detection Rate: **100%**
- Event 4 Normal: **56.3%**
- Event 5 Normal: **95.0%**

## 🔬 테스트 도구

```bash
# 5가지 방법 비교
python test_methods.py

# 결과: method_*.jpg, overlay_*.jpg
```

더 자세한 내용은 [IMPROVEMENTS.md](IMPROVEMENTS.md) 참조
