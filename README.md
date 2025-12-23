# PYgame Minesweeper
PYgame을 이용한 지뢰찾기게임
## 프로젝트 소개
기존 지뢰 찾기에서 Contributor의 기여를 통해 5가지 신규 기능을 추가한 지뢰찾기게임

#### Prerequisites (요구 사항)
- Language: Python 3.10 
- Library: Pygame (pip install pygame)

#### 실행 방법
- python run.py

## 협업 과정
1. PM이 5개의 Issue을 생성하였습니다.
2. Contributor가 해당 저장소를 Fork하여 기능을 구현한 후 PR을 요청하였습니다.
3. PM은 제출된 PR에 대해 코드 리뷰를 진행하고 피드백을 전달하였습니다.
4. 최종 코드를 확인 후 메인 저장소에 MERGE하여 병합하였습니다.

## 기여자
- Project Manager : 정혁기
- Contributor : 하승민

## 추가된 핵심 기능
Contributor와 협업하여 구현된 5가지 핵심 기능
##### 1. 난이도 설정 기능 (#Issue-1)
- 기능 설명: 숫자 키 1(EASY), 2(NORMAL), 3(HARD)을 눌러 실시간으로 보드 크기와 지뢰 개수를 변경할 수 있습니다. 
- 구현 : 각 난이도에 맞는 보드 크기와 지뢰 개수가 즉시 적용됩니다.

- EASY(1)
<img width="411" height="496" alt="image" src="https://github.com/user-attachments/assets/4a47c771-ffa5-4837-a5d2-de8008c16bf5" />


- NORMAL(2)
<img width="685" height="774" alt="image" src="https://github.com/user-attachments/assets/cd95e7fa-c619-42a5-a1ac-996f8484a464" />


- HARD(3)
<img width="1251" height="778" alt="image" src="https://github.com/user-attachments/assets/109c52aa-8ead-47b2-b7a6-28fd8d450210" />

##### 2. 힌트(Hint) 시스템(#Issue-2)
- 기능 설명 : 게임이 어려울 때 Q키를 누르면 지뢰가 없는 안전한 칸을 임의로 하나 찾아 하이라이트 해줍니다.
- 구현 : 한 게임당 1회 사용 가능하며,파란색으로 하이라이트 되어 시각적으로 도움을 줍니다.

<img width="687" height="778" alt="image" src="https://github.com/user-attachments/assets/416da363-bb9b-4bd9-b750-2e3f0e6f07e2" />

##### 3. 난이도별 최고 기록(BEST Time) 저장(#Issue-3)
- 기능 설명 : 게임 클리어 시 최단 기록을 best_time.json파일에 저장하고 화면 상단에 표시합니다.
- 구현 : JSON 포맷을 사용하여 게임을 종료한 후 다시 실행해도 이전 기록이 유지됩니다.

<img width="135" height="46" alt="image" src="https://github.com/user-attachments/assets/5bb25fd4-df84-47f2-b586-82c6e6dc7ed6" />


##### 4. 정지(Pause) 기능(#Issue-4)
- 기능 설명 : 게임 진행 중 W키를 누르면 타이머가 멈추며 일시 정지됩니다. 이때 화면 중앙에 "WAIT" 문구가 표시되어 현재 상태를 알린다.
- 재개 : W키를 다시 누르면 "WAIT"표시가 사라지고 타이머가 멈췄던 시점부터 다시 작동하며 타이머가 재개됩니다.

<img width="687" height="778" alt="image" src="https://github.com/user-attachments/assets/86433979-b623-46fe-9686-b329f680d9ae" />

##### 5. 우클릭 3단계 마킹 시스템(#Issue-5)
- 기능 설명 : 셀 우클릭시 상태가 순환되며 플레이에 도움을 준다.
- 순환 과정 : 없음 -> 깃발 -> 물음표(?) -> 없음 순으로 순환된다.
- 지뢰 개수
  - 깃발 : 왼쪽 상단의 지뢰 개수가 -1 되며 감소한다.
  - 물음표(?) : 왼쪽 상단의 지뢰 개수가 감소되지 않는다.
 
- 깃발
<img width="688" height="772" alt="image" src="https://github.com/user-attachments/assets/f035ea65-6d5c-4eaa-84a7-8d5c2f44fa20" />

- 물음표(?)
<img width="689" height="776" alt="image" src="https://github.com/user-attachments/assets/5e97b8ba-d057-465a-8e0d-80999880462c" />
