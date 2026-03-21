# Machine Learning Anomaly Detection Plan

## 🎯 **Goal**
Automatically learn normal sales patterns and detect anomalies without manual rule creation.

---

## 📊 **Overview**

### **What is Anomaly Detection?**
The system will:
1. **Learn** what "normal" sales look like over time
2. **Detect** when data deviates significantly from normal
3. **Alert** you automatically when anomalies occur
4. **Adapt** as patterns change (seasonality, trends)

### **Benefits:**
- ✅ No manual rules needed
- ✅ Catches unknown patterns
- ✅ Adapts to business changes
- ✅ Reduces false positives over time
- ✅ Predicts future issues

---

## 🧠 **Approach: Simple to Advanced**

### **Phase 1: Statistical Anomaly Detection** (EASIEST - Start Here!)
**No ML library needed, just statistics**

```python
import numpy as np
from datetime import datetime, timedelta
import json

class StatisticalAnomalyDetector:
    """Simple statistical anomaly detection using Z-scores"""
    
    def __init__(self, history_days=30):
        self.history_days = history_days
        self.historical_data = []
        
    def load_historical_data(self, sheet_id):
        """Load last 30 days of data from Google Sheets"""
        historical_data = {}
        
        # Fetch data for last 30 days
        for i in range(self.history_days):
            date = datetime.now() - timedelta(days=i)
            tab_name = f"{date.month}-{date.day}"
            
            try:
                # Read from sheet
                data = self.read_sheet_data(sheet_id, tab_name)
                historical_data[str(date.date())] = data
            except:
                continue
        
        return historical_data
    
    def calculate_baseline(self, historical_data, store, cookie):
        """Calculate mean and std deviation for a store/cookie combo"""
        values = []
        
        for date, data in historical_data.items():
            if store in data and cookie in data[store]:
                values.append(data[store][cookie])
        
        if len(values) < 7:  # Need at least 7 days
            return None, None
        
        mean = np.mean(values)
        std = np.std(values)
        
        return mean, std
    
    def detect_anomaly(self, value, mean, std, threshold=3.0):
        """Detect if value is anomalous using Z-score"""
        if mean is None or std is None or std == 0:
            return False, 0
        
        # Calculate Z-score
        z_score = abs(value - mean) / std
        
        # If Z-score > threshold, it's anomalous
        is_anomaly = z_score > threshold
        
        return is_anomaly, z_score
    
    def check_current_data(self, current_data, historical_data):
        """Check current data against historical patterns"""
        anomalies = []
        
        for store, cookies in current_data.items():
            for cookie, value in cookies.items():
                # Calculate baseline from history
                mean, std = self.calculate_baseline(
                    historical_data, store, cookie
                )
                
                if mean is not None:
                    is_anomaly, z_score = self.detect_anomaly(
                        value, mean, std, threshold=3.0
                    )
                    
                    if is_anomaly:
                        anomalies.append({
                            'store': store,
                            'cookie': cookie,
                            'value': value,
                            'expected': mean,
                            'std_dev': std,
                            'z_score': z_score,
                            'severity': 'HIGH' if z_score > 4 else 'MEDIUM'
                        })
        
        return anomalies

# Usage Example:
detector = StatisticalAnomalyDetector(history_days=30)
historical_data = detector.load_historical_data(SHEET_ID)
anomalies = detector.check_current_data(current_sales_data, historical_data)

for anomaly in anomalies:
    print(f"🚨 ANOMALY: {anomaly['store']} {anomaly['cookie']}")
    print(f"   Value: {anomaly['value']}, Expected: {anomaly['expected']:.1f}")
    print(f"   Z-Score: {anomaly['z_score']:.2f} ({anomaly['severity']})")
```

**Pros:**
- ✅ Simple to understand
- ✅ No ML dependencies
- ✅ Fast to implement
- ✅ Works well for basic cases

**Cons:**
- ❌ Assumes normal distribution
- ❌ Doesn't handle seasonality well
- ❌ Can't detect complex patterns

---

### **Phase 2: Time Series Anomaly Detection** (INTERMEDIATE)
**Uses basic ML libraries (scikit-learn)**

```python
from sklearn.ensemble import IsolationForest
import pandas as pd
import numpy as np

class TimeSeriesAnomalyDetector:
    """ML-based anomaly detection for time series data"""
    
    def __init__(self):
        # Isolation Forest: Great for anomaly detection
        self.model = IsolationForest(
            contamination=0.1,  # Expect 10% of data to be anomalies
            random_state=42
        )
        self.is_trained = False
    
    def prepare_features(self, data):
        """Convert raw data to ML features"""
        features = []
        
        for date, stores in data.items():
            dt = datetime.strptime(date, '%Y-%m-%d')
            
            for store, cookies in stores.items():
                total = sum(cookies.values())
                
                # Create feature vector
                feature = {
                    'day_of_week': dt.weekday(),
                    'day_of_month': dt.day,
                    'month': dt.month,
                    'is_weekend': 1 if dt.weekday() >= 5 else 0,
                    'total_sales': total,
                    'cookie_variety': len(cookies),
                    # Add cookie-specific features
                    **{f'cookie_{k}': v for k, v in cookies.items()}
                }
                
                features.append(feature)
        
        # Convert to DataFrame
        df = pd.DataFrame(features)
        return df
    
    def train(self, historical_data):
        """Train the model on historical data"""
        print("🧠 Training ML model on historical data...")
        
        # Prepare features
        X = self.prepare_features(historical_data)
        
        # Train model
        self.model.fit(X)
        self.feature_columns = X.columns.tolist()
        self.is_trained = True
        
        print(f"✅ Model trained on {len(X)} data points")
    
    def predict_anomalies(self, current_data):
        """Predict if current data is anomalous"""
        if not self.is_trained:
            raise ValueError("Model not trained yet!")
        
        # Prepare features
        X = self.prepare_features({'today': current_data})
        
        # Ensure same features as training
        for col in self.feature_columns:
            if col not in X.columns:
                X[col] = 0
        X = X[self.feature_columns]
        
        # Predict (-1 = anomaly, 1 = normal)
        predictions = self.model.predict(X)
        scores = self.model.score_samples(X)
        
        anomalies = []
        for i, (pred, score) in enumerate(zip(predictions, scores)):
            if pred == -1:  # Anomaly detected
                anomalies.append({
                    'index': i,
                    'score': score,
                    'severity': 'HIGH' if score < -0.5 else 'MEDIUM'
                })
        
        return anomalies
    
    def save_model(self, filepath):
        """Save trained model to disk"""
        import pickle
        with open(filepath, 'wb') as f:
            pickle.dump(self.model, f)
    
    def load_model(self, filepath):
        """Load trained model from disk"""
        import pickle
        with open(filepath, 'rb') as f:
            self.model = pickle.load(f)
        self.is_trained = True

# Usage:
detector = TimeSeriesAnomalyDetector()
detector.train(historical_data)
anomalies = detector.predict_anomalies(current_sales_data)
detector.save_model('anomaly_model.pkl')
```

**Pros:**
- ✅ Handles complex patterns
- ✅ Considers multiple features
- ✅ Adapts to seasonality
- ✅ Low false positive rate

**Cons:**
- ❌ Needs scikit-learn library
- ❌ Requires training data
- ❌ More complex to debug

---

### **Phase 3: Deep Learning Anomaly Detection** (ADVANCED)
**Uses LSTM neural networks (TensorFlow/PyTorch)**

```python
import torch
import torch.nn as nn
import numpy as np

class LSTMAnomalyDetector(nn.Module):
    """LSTM-based anomaly detection for time series"""
    
    def __init__(self, input_size, hidden_size=64, num_layers=2):
        super().__init__()
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True
        )
        
        self.fc = nn.Linear(hidden_size, input_size)
    
    def forward(self, x):
        # LSTM forward pass
        lstm_out, _ = self.lstm(x)
        
        # Prediction
        prediction = self.fc(lstm_out[:, -1, :])
        
        return prediction
    
    def train_model(self, data, epochs=100):
        """Train LSTM on historical sequences"""
        optimizer = torch.optim.Adam(self.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        
        for epoch in range(epochs):
            # Forward pass
            predictions = self(data)
            loss = criterion(predictions, data)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            if epoch % 10 == 0:
                print(f"Epoch {epoch}, Loss: {loss.item():.4f}")
    
    def detect_anomaly(self, sequence, threshold=0.1):
        """Detect anomalies using reconstruction error"""
        self.eval()
        
        with torch.no_grad():
            prediction = self(sequence)
            error = torch.abs(prediction - sequence[-1])
            
            # If reconstruction error > threshold, it's anomalous
            is_anomaly = error.mean() > threshold
            
            return is_anomaly, error.mean().item()

# Usage:
model = LSTMAnomalyDetector(input_size=13)  # 13 cookie types
model.train_model(historical_sequences)
is_anomaly, error = model.detect_anomaly(current_sequence)
```

**Pros:**
- ✅ State-of-the-art accuracy
- ✅ Learns complex temporal patterns
- ✅ Handles multivariate time series
- ✅ Excellent for long-term trends

**Cons:**
- ❌ Requires significant training data (6+ months)
- ❌ Complex setup (TensorFlow/PyTorch)
- ❌ Computationally expensive
- ❌ Needs GPU for training

---

## 📋 **Implementation Roadmap**

### **Step 1: Data Collection (Week 1)**
```python
# Create historical data storage
historical_data_store = {
    'version': '1.0',
    'data': {},
    'metadata': {
        'start_date': '2025-10-01',
        'last_updated': datetime.now().isoformat()
    }
}

def collect_daily_data(sales_data):
    """Collect and store daily data for ML training"""
    today = datetime.now().date()
    
    # Store today's data
    historical_data_store['data'][str(today)] = {
        'timestamp': datetime.now().isoformat(),
        'sales': sales_data,
        'totals': {
            store: sum(cookies.values()) 
            for store, cookies in sales_data.items()
        }
    }
    
    # Save to file
    with open('historical_data.json', 'w') as f:
        json.dump(historical_data_store, f, indent=2)
    
    print(f"✅ Collected data for {today}")
```

### **Step 2: Implement Statistical Detector (Week 2)**
- Start with simple Z-score based detection
- Collect 2 weeks of data
- Test and tune thresholds
- Integrate with main script

### **Step 3: Add ML Detector (Week 3-4)**
- Install scikit-learn on VM
- Implement Isolation Forest
- Train on collected data
- A/B test vs statistical method

### **Step 4: Continuous Learning (Week 5+)**
- Retrain model weekly
- Track accuracy metrics
- Tune hyperparameters
- Expand features

---

## 🔧 **Practical Implementation for Your System**

### **Option 1: Quick Start (Recommended)** ⭐

```python
# Add to vm_inventory_updater.py

class SimpleAnomalyDetector:
    """Simple but effective anomaly detection"""
    
    def __init__(self, history_file='sales_history.json'):
        self.history_file = history_file
        self.history = self.load_history()
    
    def load_history(self):
        """Load historical sales data"""
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except:
            return {'stores': {}}
    
    def add_todays_data(self, sales_data):
        """Add today's data to history"""
        today = datetime.now().date().isoformat()
        
        for store, cookies in sales_data.items():
            if store not in self.history['stores']:
                self.history['stores'][store] = {}
            
            for cookie, count in cookies.items():
                if cookie not in self.history['stores'][store]:
                    self.history['stores'][store][cookie] = []
                
                # Store as (date, value)
                self.history['stores'][store][cookie].append({
                    'date': today,
                    'value': count
                })
                
                # Keep only last 30 days
                if len(self.history['stores'][store][cookie]) > 30:
                    self.history['stores'][store][cookie].pop(0)
        
        self.save_history()
    
    def save_history(self):
        """Save history to file"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def detect_anomalies(self, sales_data):
        """Simple anomaly detection"""
        anomalies = []
        
        for store, cookies in sales_data.items():
            for cookie, value in cookies.items():
                # Get historical values
                hist_values = self.get_historical_values(store, cookie)
                
                if len(hist_values) < 7:
                    continue  # Need at least 7 days
                
                # Calculate statistics
                mean = np.mean(hist_values)
                std = np.std(hist_values)
                
                if std == 0:
                    continue
                
                # Z-score
                z = abs(value - mean) / std
                
                if z > 3:  # More than 3 standard deviations
                    anomalies.append({
                        'store': store,
                        'cookie': cookie,
                        'value': value,
                        'expected': mean,
                        'z_score': z
                    })
        
        return anomalies
    
    def get_historical_values(self, store, cookie):
        """Get last N days of values"""
        if store not in self.history['stores']:
            return []
        if cookie not in self.history['stores'][store]:
            return []
        
        return [
            item['value'] 
            for item in self.history['stores'][store][cookie]
        ]

# Integration:
detector = SimpleAnomalyDetector()

# After fetching sales data:
anomalies = detector.detect_anomalies(sales_data)

if anomalies:
    logging.warning(f"🤖 ML: Detected {len(anomalies)} anomalies!")
    for anomaly in anomalies:
        logging.warning(
            f"   {anomaly['store']} {anomaly['cookie']}: "
            f"{anomaly['value']} (expected ~{anomaly['expected']:.1f}, "
            f"z-score: {anomaly['z_score']:.2f})"
        )

# Store today's data for future learning
detector.add_todays_data(sales_data)
```

### **Option 2: Cloud-Based ML (Google Cloud AI)**

```python
from google.cloud import automl_v1

class CloudAnomalyDetector:
    """Use Google Cloud AutoML for anomaly detection"""
    
    def __init__(self, project_id, model_id):
        self.client = automl_v1.PredictionServiceClient()
        self.model_path = f"projects/{project_id}/locations/us-central1/models/{model_id}"
    
    def predict(self, sales_data):
        """Get predictions from Cloud AutoML"""
        # Prepare payload
        payload = {
            'row': {
                'values': [
                    str(v) for v in sales_data.values()
                ]
            }
        }
        
        # Get prediction
        response = self.client.predict(
            name=self.model_path,
            payload=payload
        )
        
        return response
```

---

## 📊 **Feature Engineering for Better Detection**

```python
def extract_features(sales_data, date):
    """Extract features from sales data"""
    features = {}
    
    # Time-based features
    features['day_of_week'] = date.weekday()
    features['day_of_month'] = date.day
    features['month'] = date.month
    features['is_weekend'] = 1 if date.weekday() >= 5 else 0
    features['is_holiday'] = check_if_holiday(date)
    
    # Sales-based features
    for store, cookies in sales_data.items():
        total = sum(cookies.values())
        features[f'{store}_total'] = total
        features[f'{store}_variety'] = len([c for c in cookies.values() if c > 0])
        
        # Top cookie
        if cookies:
            top_cookie = max(cookies, key=cookies.get)
            features[f'{store}_top_cookie'] = top_cookie
            features[f'{store}_top_count'] = cookies[top_cookie]
    
    # Aggregate features
    all_totals = [sum(c.values()) for c in sales_data.values()]
    features['total_all_stores'] = sum(all_totals)
    features['avg_per_store'] = np.mean(all_totals)
    features['std_per_store'] = np.std(all_totals)
    
    return features
```

---

## 🎯 **Success Metrics**

Track these to measure ML performance:

1. **Accuracy**: % of anomalies correctly identified
2. **Precision**: % of alerts that are real issues
3. **Recall**: % of real issues that are detected
4. **False Positive Rate**: % of false alarms (target: <10%)
5. **Detection Time**: How quickly anomalies are caught
6. **Adaptation Rate**: How fast model learns new patterns

---

## 💡 **Best Practices**

1. **Start Simple**: Begin with statistical methods before ML
2. **Collect Data First**: Need 2+ weeks before meaningful ML
3. **Human in the Loop**: Always review ML predictions
4. **Continuous Retraining**: Retrain weekly with new data
5. **A/B Testing**: Compare ML vs rule-based side-by-side
6. **Explainability**: Understand why ML flagged something
7. **Graceful Degradation**: Fall back to rules if ML fails

---

## 🚀 **Quick Start Checklist**

- [ ] Add data collection to main script
- [ ] Collect 2 weeks of historical data
- [ ] Implement SimpleAnomalyDetector class
- [ ] Test on known anomalies
- [ ] Tune detection thresholds
- [ ] Add ML alerts to logs
- [ ] Set up weekly retraining
- [ ] Monitor false positive rate
- [ ] Expand features based on results
- [ ] Consider advanced ML models

---

## 📚 **Required Libraries**

### **Phase 1 (Statistical)**
```bash
pip install numpy
```

### **Phase 2 (ML)**
```bash
pip install scikit-learn pandas numpy
```

### **Phase 3 (Deep Learning)**
```bash
pip install torch numpy pandas
# or
pip install tensorflow numpy pandas
```

---

## 🔮 **Future Enhancements**

1. **Predictive Alerts**: Predict tomorrow's sales
2. **Root Cause Analysis**: Explain why anomaly occurred
3. **Automatic Remediation**: Suggest fixes
4. **Multi-Store Correlation**: Detect system-wide issues
5. **Customer Behavior Modeling**: Understand buying patterns
6. **Inventory Optimization**: Recommend stock levels
7. **Demand Forecasting**: Predict busy periods
8. **Real-time Streaming**: Process data as it arrives

---

## 💰 **Cost Considerations**

### **On-Premises (Current GCP VM)**
- ✅ Free (already have VM)
- ✅ Simple models work fine
- ⚠️ Limited compute for deep learning

### **Cloud ML (Google AutoML)**
- ⚠️ $20-50/month for training
- ⚠️ $0.001 per prediction
- ✅ No maintenance
- ✅ State-of-the-art models

### **Hybrid Approach** (Recommended)
- Use simple ML on VM for real-time
- Train complex models in cloud monthly
- Download model weights for VM use

---

## 🎓 **Learning Resources**

1. **Anomaly Detection Basics**: 
   - YouTube: "StatQuest - Anomaly Detection"
   
2. **Time Series ML**:
   - Course: Google's "Time Series Forecasting"
   
3. **Practical Implementation**:
   - GitHub: "awesome-anomaly-detection"
   
4. **Your Data**:
   - Start experimenting with YOUR data!
   - Best learning is hands-on

---

## ✅ **Conclusion**

**Recommended Path:**
1. **Week 1-2**: Collect data, implement statistical detector
2. **Week 3-4**: Add simple ML (Isolation Forest)
3. **Month 2+**: Tune and optimize
4. **Month 3+**: Consider deep learning if needed

**Key Takeaway**: Start simple, iterate fast, measure everything!


