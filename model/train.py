import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

df = pd.read_csv('model/data/final_data.csv')

X = df.drop(columns=['_ID_EXAM', 'IMAGE_NAME', 'ID_PATIENT', 'CLASS_TYPE', 'RIGH/LEFT-HANDED', 'GENDER'])
y = df['CLASS_TYPE'] - 1

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

xgb_model = xgb.XGBClassifier(objective='binary:logistic',
                         n_estimators=400,
                         max_depth=7,
                         learning_rate=0.003)
xgb_model.fit(X_train, y_train)

y_pred_prob = xgb_model.predict_proba(X_test)[:, 1]
y_pred = xgb_model.predict(X_test)

# Assuming you have y_test (true labels) and y_pred (predicted labels)

# Accuracy
accuracy = accuracy_score(y_test, y_pred)

# Precision
precision = precision_score(y_test, y_pred)

# Recall
recall = recall_score(y_test, y_pred)

# F1-score
f1 = f1_score(y_test, y_pred)

# ROC AUC score
roc_auc = roc_auc_score(y_test, y_pred_prob)  # Use y_pred_prob for probabilities

# Confusion matrix
conf_matrix = confusion_matrix(y_test, y_pred)

# Print the metrics
print(f"Accuracy: {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall: {recall:.4f}")
print(f"F1-score: {f1:.4f}")
print(f"ROC AUC: {roc_auc:.4f}")
print("Confusion Matrix:")
print(conf_matrix)

xgb_model.save_model('/model/data/xgboost_model.json')