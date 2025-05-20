# Moved to backend/utils/mediapipe_face_demo.py cv2
# Moved to backend/utils/mediapipe_face_demo.py mediapipe as mp

mp_face = mp.solutions.face_detection
mp_draw = mp.solutions.drawing_utils

# Initialize webcam
cap = cv2.VideoCapture(0)

with mp_face.FaceDetection(
    model_selection=0,  # 0 for short-range, 1 for full-range
    min_detection_confidence=0.5
) as face_detection:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detection.process(rgb)
        if results.detections:
            for detection in results.detections:
                mp_draw.draw_detection(frame, detection)
        cv2.imshow('MediaPipe Face Detection Demo', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
cap.release()
cv2.destroyAllWindows()
