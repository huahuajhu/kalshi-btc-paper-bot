"""
Example: Using ML-Ready Dataset for Prediction

This example demonstrates how to use the generated dataset
for machine learning tasks like predicting market outcomes.
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report


def load_and_prepare_data(dataset_path='data/ml_dataset.csv'):
    """
    Load the generated dataset and prepare it for ML.
    
    Args:
        dataset_path: Path to the ML dataset CSV
        
    Returns:
        X: Features DataFrame
        y: Labels Series
        
    Raises:
        ValueError: If required columns are missing from the dataset
    """
    # Load dataset
    df = pd.read_csv(dataset_path)
    
    print(f"Dataset loaded: {len(df)} samples")
    print(f"Features: {df.columns.tolist()}")
    
    # Define feature columns (exclude metadata and label)
    feature_columns = [
        'btc_return_5m',
        'btc_return_15m',
        'yes_price',
        'no_price',
        'spread',
        'volatility'
    ]
    
    # Validate that required columns exist
    missing_features = [col for col in feature_columns if col not in df.columns]
    if missing_features:
        raise ValueError(f"Missing required feature columns: {missing_features}")
    
    if 'label' not in df.columns:
        raise ValueError("Missing required 'label' column")
    
    # Prepare features and labels
    X = df[feature_columns]
    y = df['label']
    
    return X, y


def train_simple_model(X, y):
    """
    Train a simple Random Forest classifier.
    
    Note: This example uses random train/test split for simplicity. For time-series
    data like this, temporal splitting (training on earlier dates, testing on later
    dates) would be more appropriate to avoid data leakage where the model learns
    from future data to predict past outcomes.
    
    Args:
        X: Features
        y: Labels
        
    Returns:
        model: Trained model
        X_test: Test features
        y_test: Test labels
    """
    # Split data - using random split for demonstration
    # For production use, consider temporal split: train on early data, test on later data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    print(f"\nTraining set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")
    print(f"Note: Using random split. Consider temporal split for production.")
    
    # Train model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    return model, X_test, y_test


def evaluate_model(model, X_test, y_test):
    """
    Evaluate the trained model.
    
    Args:
        model: Trained model
        X_test: Test features
        y_test: Test labels
    """
    # Make predictions
    y_pred = model.predict(X_test)
    
    # Calculate accuracy
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"\nModel Performance:")
    print(f"  Accuracy: {accuracy:.2%}")
    
    # Get unique classes in the data
    unique_classes = sorted(set(y_test) | set(y_pred))
    
    if len(unique_classes) > 1:
        print("\nClassification Report:")
        target_names = ['NO wins', 'YES wins'] if len(unique_classes) == 2 else None
        print(classification_report(y_test, y_pred, target_names=target_names))
    else:
        print(f"\nNote: Only one class ({unique_classes[0]}) present in test set.")
        print("Classification report not meaningful with single class.")
    
    # Feature importance
    feature_names = X_test.columns
    importances = model.feature_importances_
    
    print("\nFeature Importance:")
    for name, importance in sorted(zip(feature_names, importances), 
                                   key=lambda x: x[1], reverse=True):
        print(f"  {name}: {importance:.4f}")


def main():
    """Main function to demonstrate ML pipeline."""
    
    print("=" * 60)
    print("ML Dataset Example: Market Outcome Prediction")
    print("=" * 60)
    
    try:
        # Load and prepare data
        X, y = load_and_prepare_data()
        
        # Check if we have enough data
        if len(X) < 10:
            print("\nWarning: Dataset is too small for meaningful ML.")
            print("Generate more data by running the simulator on a larger dataset.")
            return
        
        # Train model
        model, X_test, y_test = train_simple_model(X, y)
        
        # Evaluate model
        evaluate_model(model, X_test, y_test)
        
        print("\n" + "=" * 60)
        print("Example completed successfully!")
        print("=" * 60)
        
    except FileNotFoundError:
        print("\nError: Dataset file not found!")
        print("Please run 'python generate_dataset.py' first to create the dataset.")
    except ValueError as e:
        print(f"\nError: {e}")
        print("Please ensure the dataset was generated correctly.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
