import os
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import numpy as np

class MLService:
    def __init__(self, base_dir=None):
        # -------------------------------
        # Base directory pour CSV et modèle
        # -------------------------------
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.csv_file = os.path.join(self.base_dir, "analyzer_dataset.csv")
        self.model_file = os.path.join(self.base_dir, "ml_model.pkl")
        self.model = None

    # -------------------------------
    # Entraînement du modèle à partir du CSV
    # -------------------------------
    def train_from_csv(self):
        if not os.path.exists(self.csv_file):
            raise FileNotFoundError(f"CSV file not found: {self.csv_file}")
        print("[ML Service] Loading CSV for training...")
        df = pd.read_csv(self.csv_file)
        df = df.fillna(0)

        # Génération des features temporelles simples à partir des 3 dernières mesures
        df["cpu_delta1"] = df["cpu"].diff().fillna(0)
        df["memory_delta1"] = df["memory"].diff().fillna(0)
        df["cpu_delta2"] = df["cpu"].diff(periods=2).fillna(0)
        df["memory_delta2"] = df["memory"].diff(periods=2).fillna(0)

        # Target : anomalie CPU à la prochaine mesure
        df["cpu_anomaly_next"] = df["cpu_anomaly"].shift(-1).fillna(0).astype(int)

        feature_cols = ["cpu", "memory", "service_time", "instances",
                        "cpu_delta1", "memory_delta1", "cpu_delta2", "memory_delta2"]

        X = df[feature_cols]
        y = df["cpu_anomaly_next"]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        print("[ML Service] Training finished. Evaluation:")
        print(classification_report(y_test, y_pred))

        self.model = model
        joblib.dump(model, self.model_file)
        print(f"[ML Service] Model saved at {self.model_file}")

    # -------------------------------
    # Charger le modèle depuis le fichier
    # -------------------------------
    def load_model(self):
        if not os.path.exists(self.model_file):
            raise FileNotFoundError(f"Model file not found: {self.model_file}")
        self.model = joblib.load(self.model_file)
        print(f"[ML Service] Model loaded from {self.model_file}")

    # -------------------------------
    # Prédire la prochaine mesure CPU à partir des 3 dernières
    # -------------------------------
    def predict_next(self, last_measures: list):
        """
        last_measures : list de 1 à 3 dictionnaires contenant les mesures les plus récentes
        exemple :
        [
            {"cpu": 50, "memory": 200, "service_time": 0.5, "instances": 2},
            {"cpu": 55, "memory": 220, "service_time": 0.6, "instances": 2},
            {"cpu": 60, "memory": 250, "service_time": 0.7, "instances": 2}
        ]
        """
        if self.model is None:
            raise Exception("Model not loaded. Call load_model() first.")

        # Préparer les features
        last_measures = last_measures[-3:]  # prendre au maximum 3 dernières
        while len(last_measures) < 3:  # si on a moins de 3 mesures, compléter par duplicata
            last_measures = [last_measures[0]] + last_measures

        m1, m2, m3 = last_measures

        # Calcul des features similaires à l'entraînement
        cpu_delta1 = m3["cpu"] - m2["cpu"]
        memory_delta1 = m3["memory"] - m2["memory"]
        cpu_delta2 = m3["cpu"] - m1["cpu"]
        memory_delta2 = m3["memory"] - m1["memory"]

        features = pd.DataFrame([[
            m3["cpu"], m3["memory"], m3["service_time"], m3["instances"],
            cpu_delta1, memory_delta1, cpu_delta2, memory_delta2
        ]], columns=["cpu", "memory", "service_time", "instances",
                     "cpu_delta1", "memory_delta1", "cpu_delta2", "memory_delta2"])

        prediction = self.model.predict(features)[0]
        return int(prediction)


# -------------------------------
# Mode autonome pour l'entraînement
# -------------------------------
if __name__ == "__main__":
    TRAINING = False  # mettre False pour juste charger le modèle

    ml_service = MLService()

    if TRAINING:
        ml_service.train_from_csv()
    else:
        ml_service.load_model()
        # exemple de prédiction fictive
        example = [
            {"cpu": 50, "memory": 200, "service_time": 0.5, "instances": 2},
            {"cpu": 55, "memory": 220, "service_time": 0.6, "instances": 2},
            {"cpu": 60, "memory": 250, "service_time": 0.7, "instances": 2}
        ]
        pred = ml_service.predict_next(example)
        print(f"Predicted next CPU anomaly: {pred}")
