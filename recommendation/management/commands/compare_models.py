# Set environment variables first, before any other imports
import os
import sys
import matplotlib as mpl

# Fix the CPU core detection issue with LightGBM on Windows
os.environ['LOKY_MAX_CPU_COUNT'] = str(os.cpu_count() or 4)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
# Force matplotlib to use a specific backend that works well with various character sets
mpl.use('Agg')

# recommendation/management/commands/compare_models.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
import logging
import time
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib
import traceback
import psutil
import gc
import pickle
from matplotlib.colors import LinearSegmentedColormap
import warnings
from sklearn.ensemble import GradientBoostingRegressor
import xgboost as xgb

# Use try-except for LightGBM to handle potential import issues
try:
    import lightgbm as lgb

    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    print("LightGBM is not available, related models will be skipped")

try:
    import tensorflow as tf

    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("TensorFlow is not available, neural network models will be skipped")

# Project imports - use dummy imports if running standalone
try:
    from anime.models import Anime
    from recommendation.models import UserRating
except ImportError:
    print("Warning: Running in standalone mode without Django models")

logger = logging.getLogger('django')


class Command(BaseCommand):
    help = 'Compare different machine learning models on the anime recommendation task'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_english = True  # Always use English by default
        self.setup_global_font_config()
        self.suppress_warnings()

    def suppress_warnings(self):
        """Suppress various warnings that might clutter the output"""
        # Suppress Python warnings
        warnings.filterwarnings('ignore', category=FutureWarning)
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

        # Set pandas display options
        pd.set_option('display.width', 120)
        pd.set_option('display.precision', 4)

        # Set numpy print options
        np.set_printoptions(precision=4, suppress=True)

        # Set TensorFlow environment variables
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # 0=ALL, 1=INFO, 2=WARNING, 3=ERROR

    def setup_global_font_config(self):
        """Set up universal font configuration to ensure text displays properly"""
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica', 'Liberation Sans']
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['figure.dpi'] = 100
        plt.rcParams['font.size'] = 11
        plt.rcParams['axes.labelsize'] = 12
        plt.rcParams['axes.titlesize'] = 14
        plt.rcParams['xtick.labelsize'] = 10
        plt.rcParams['ytick.labelsize'] = 10
        plt.rcParams['legend.fontsize'] = 10
        plt.rcParams['figure.titlesize'] = 16
        plt.rcParams['figure.constrained_layout.use'] = False

    def translate(self, text):
        """Always translate text to English for consistent display"""
        translations = self.get_translations()
        return translations.get(text, text)

    def get_translations(self):
        """Return a dictionary mapping Chinese labels to English equivalents"""
        return {
            # General labels
            '标准化性能指标 (值越高越好)': 'Normalized Performance (Higher is Better)',
            '模型性能统一标准比较': 'Unified Model Performance Comparison',
            '注: 所有指标都已标准化到0-1区间，其中1代表最佳性能。': 'Note: All metrics normalized to 0-1 range, with 1 representing best performance.',
            '对于如RMSE等"越低越好"的指标，已进行反向标准化，使其符合"值越大越好"的统一标准。': 'For metrics like RMSE where "lower is better", values have been inverted so that higher values represent better performance.',

            # Metrics
            'RMSE\n精确度': 'RMSE\nAccuracy',
            'MAE\n稳健性': 'MAE\nRobustness',
            'R²\n解释力': 'R²\nExplanatory Power',
            '训练时间\n训练效率': 'Training Time\nEfficiency',
            '预测时间\n推理效率': 'Prediction Time\nEfficiency',
            '内存\n资源效率': 'Memory\nEfficiency',

            # Chart titles
            '模型性能多维度分析': 'Multidimensional Model Performance Analysis',
            '全维度性能雷达图': 'Full Performance Radar Chart',
            '预测精度指标雷达图': 'Prediction Accuracy Metrics',
            '计算效率指标雷达图': 'Computational Efficiency Metrics',
            '资源消耗指标雷达图': 'Resource Consumption Metrics',

            # Other common translations
            '模型': 'Model',
            '误差值': 'Error Value',
            '均方根误差(RMSE)\n越低越好': 'RMSE\nLower is Better',
            '决定系数(R²)\n越高越好': 'R²\nHigher is Better',
            '训练与预测时间对比': 'Training vs Prediction Time',
            '内存使用情况\n越低越好': 'Memory Usage\nLower is Better',
            '训练时间': 'Training Time',
            '预测时间': 'Prediction Time',
            '内存使用(MB)': 'Memory Usage (MB)',
            '特征重要性': 'Feature Importance',
            '特征': 'Feature',
            '重要性值': 'Importance Value',
            '高精度-高速区': 'High Accuracy-Fast Zone',
            '中精度-高速区': 'Medium Accuracy-Fast Zone',
            '高精度-慢速区': 'High Accuracy-Slow Zone',
            '低精度-慢速区': 'Low Accuracy-Slow Zone',
            '气泡大小': 'Bubble Size',
            '内存效率': 'Memory Efficiency',
            '用户平均评分': 'User Avg Rating',
            '动漫平均评分': 'Anime Avg Rating',
            '用户评分标准差': 'User Rating Std',
            '动漫评分标准差': 'Anime Rating Std',
            '用户评分数': 'User Rating Count',
            '动漫评分数': 'Anime Rating Count',
            '集数': 'Episodes',
            '会员数': 'Member Count',
            '类型编码': 'Type Encoded',
            '模型排名在各性能指标上的比较': 'Model Performance Ranking Comparison',
            '平均排名': 'Average Rank',
            '排名': 'Rank',
            '加权得分': 'Weighted Score',
            '模型综合评分对比': 'Model Comprehensive Score Comparison',
            '评分指标': 'Scoring Metrics',
            '评分权重分配': 'Score Weight Distribution',
            '评分权重': 'Score Weights',
            '性能权衡分析': 'Performance Trade-off Analysis',
            '模型性能权衡分析': 'Model Performance Trade-off Analysis',
            '精度 vs 训练时间 vs 内存占用': 'Accuracy vs Training Time vs Memory Usage',
            '模型性能多维度权衡分析': 'Multidimensional Performance Trade-off Analysis',
            '气泡大小表示内存效率': 'Bubble size represents memory efficiency',
            '模型预测分布与实际分布对比': 'Model Prediction vs Actual Distribution Comparison',
            '模型预测残差分析': 'Model Prediction Residual Analysis',
            '残差': 'Residual',
            '预测值': 'Predicted Value',
            '实际值': 'Actual Value',
            '分位数': 'Quantile',
            '密度': 'Density',
            '值': 'Value',
            '预测分位数': 'Predicted Quantile',
            '实际分位数': 'Actual Quantile',
            '预测分布': 'Prediction Distribution',
            '误差分布': 'Error Distribution',

            # Additional translations
            '模型性能对比': 'Model Performance Comparison',
            '模型预测误差分析': 'Model Prediction Error Analysis',
            '模型预测分位数分析(Q-Q图)': 'Model Prediction Quantile Analysis (Q-Q Plot)',
            '模型在各性能指标上的排名比较': 'Model Performance Ranking Comparison',
            '不同模型的特征重要性对比分析': 'Feature Importance Comparison Across Models',
            '标准化特征重要性': 'Normalized Feature Importance',
        }

    def suppress_tensorflow_warnings(self):
        """Suppress TensorFlow warnings and properly configure GPU usage"""
        # Set TensorFlow logging level
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

        try:
            import tensorflow as tf

            # Disable eager execution warning - using compat.v1 API
            tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)

            # Configure GPU memory growth
            gpus = tf.config.experimental.list_physical_devices('GPU')
            if gpus:
                try:
                    for gpu in gpus:
                        tf.config.experimental.set_memory_growth(gpu, True)
                    self.stdout.write(self.style.SUCCESS(f"✅ TensorFlow configured with {len(gpus)} GPUs"))
                except RuntimeError as e:
                    self.stdout.write(self.style.WARNING(f"⚠️ GPU memory growth setting failed: {e}"))
            else:
                self.stdout.write(self.style.WARNING("ℹ️ No GPU available for TensorFlow"))

            return True
        except ImportError:
            return False
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️ TensorFlow configuration error: {e}"))
            return False
    def add_arguments(self, parser):
        parser.add_argument('--kaggle-data', type=str, default=None,
                            help='Kaggle dataset directory path')
        parser.add_argument('--sample-size', type=int, default=100000,
                            help='Number of records to sample from Kaggle dataset, default 100000')
        parser.add_argument('--test-size', type=float, default=0.2,
                            help='Test set proportion, default 0.2')
        parser.add_argument('--use-local', action='store_true',
                            help='Use local database data')
        parser.add_argument('--output-dir', type=str, default='model_comparison',
                            help='Output directory, default "model_comparison"')
        parser.add_argument('--save-best', action='store_true',
                            help='Save the best performing model')
        parser.add_argument('--english', action='store_true',
                            help='Force English labels for all charts')
        parser.add_argument('--verbose', action='store_true',
                            help='Enable verbose output')
        parser.add_argument('--cpu-only', action='store_true',
                            help='Force CPU usage even if GPU is available')

    def handle(self, *args, **options):
        # Configure TensorFlow and other libraries
        self.suppress_tensorflow_warnings()

        # Get parameters
        kaggle_data = options['kaggle_data']
        sample_size = options['sample_size']
        test_size = options['test_size']
        use_local = options['use_local']
        output_dir = options['output_dir']
        save_best = options['save_best']
        self.use_english = options['english'] or True
        verbose = options['verbose']
        cpu_only = options['cpu_only']

        # Force CPU if requested
        if cpu_only:
            os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
            self.stdout.write(self.style.WARNING("⚠️ Forcing CPU usage as requested"))

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Find Kaggle dataset
        if not kaggle_data:
            # Try several possible locations
            possible_paths = [
                os.path.join(settings.BASE_DIR if 'settings' in dir() else '.', 'archive'),
                os.path.join('D:', os.sep, 'dmos', 'anime_rec_system', 'archive'),
                os.path.join('.', 'archive')
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    kaggle_data = path
                    break

        # Print experiment configuration
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS(f'🔍 Anime Recommendation System Model Comparison [{timezone.now()}]'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        if kaggle_data:
            self.stdout.write(f'📊 Kaggle data path: {kaggle_data}')
            self.stdout.write(f'📊 Sample size: {sample_size} records')
        if use_local:
            self.stdout.write(f'📊 Using local database data')
        self.stdout.write(f'📊 Test set proportion: {test_size}')
        self.stdout.write(f'📊 Output directory: {output_dir}')
        self.stdout.write(f'📊 Save best model: {"Yes" if save_best else "No"}')
        self.stdout.write(f'📊 Chart labels: {"English" if self.use_english else "Original"}')

        # Load data
        X_train, X_test, y_train, y_test, feature_names = self.load_data(
            kaggle_data, sample_size, test_size, use_local
        )

        if X_train is None:
            self.stdout.write(self.style.ERROR('❌ Data loading failed, experiment terminated'))
            return

        self.stdout.write(self.style.SUCCESS(f'✅ Data loaded, training set: {X_train.shape}, test set: {X_test.shape}'))

        # Get input dimension for neural network
        input_dim = X_train.shape[1]

        # Define models to compare
        models = self.get_models(feature_names, input_dim)

        # Run experiment
        results = self.run_experiment(models, X_train, X_test, y_train, y_test)

        # Generate visualizations
        self.visualize_comparison(results, output_dir)

        # Visualize feature importance for tree-based models
        self.visualize_feature_importance(models, feature_names, output_dir)

        # Visualize prediction distribution
        self.visualize_prediction_distribution(models, X_test, y_test, output_dir)

        # Add new performance trend line charts visualization
        self.visualize_performance_trends(results, output_dir)

        # Save best model
        if save_best:
            self.save_best_model(results, models, output_dir, feature_names)

        # Show summary
        self.print_summary(results)

    def load_data(self, kaggle_data, sample_size, test_size, use_local):
        """Load and preprocess data with improved error handling and validation"""
        try:
            # Initialize variables
            X, y, feature_names = None, None, None

            # Load Kaggle data
            if kaggle_data and os.path.exists(kaggle_data):
                self.stdout.write('🔄 Loading data from Kaggle dataset...')
                anime_csv = os.path.join(kaggle_data, 'anime.csv')
                rating_csv = os.path.join(kaggle_data, 'rating.csv')

                if not os.path.exists(anime_csv) or not os.path.exists(rating_csv):
                    self.stdout.write(
                        self.style.WARNING(f"❌ Kaggle data files don't exist: {anime_csv} or {rating_csv}"))
                else:
                    try:
                        # Load rating data with error handling
                        rating_df = pd.read_csv(rating_csv, encoding='utf-8')
                        self.stdout.write(f"📊 Loaded {len(rating_df)} ratings from Kaggle data")

                        # Remove -1 ratings
                        rating_df = rating_df[rating_df['rating'] > 0]
                        self.stdout.write(f"📊 Found {len(rating_df)} valid ratings after filtering")

                        # Sample
                        if sample_size and sample_size < len(rating_df):
                            rating_df = rating_df.sample(sample_size, random_state=42)
                            self.stdout.write(f"📊 Sampled {len(rating_df)} ratings")

                        # Load anime data
                        anime_df = pd.read_csv(anime_csv, encoding='utf-8')
                        self.stdout.write(f"📊 Loaded {len(anime_df)} anime entries from Kaggle data")

                        # Process features
                        X_kaggle, y_kaggle, feature_names_kaggle = self.prepare_kaggle_features(anime_df, rating_df)

                        if X_kaggle is not None:
                            X, y, feature_names = X_kaggle, y_kaggle, feature_names_kaggle
                            self.stdout.write(
                                self.style.SUCCESS(f'✅ Kaggle data processed: {len(y)} records, {X.shape[1]} features'))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'❌ Error processing Kaggle data: {str(e)}'))
                        traceback.print_exc()

            # Load local data
            if use_local:
                self.stdout.write('🔄 Loading data from local database...')
                try:
                    X_local, y_local, feature_names_local = self.prepare_local_features()

                    if X_local is not None:
                        # If we already have Kaggle data, decide which to use
                        if X is not None and y is not None:
                            # Use the dataset with more records
                            if len(y_local) > len(y):
                                X, y, feature_names = X_local, y_local, feature_names_local
                                self.stdout.write(f'✅ Using local data ({len(y)} records) instead of Kaggle data')
                            else:
                                self.stdout.write(
                                    f'✅ Using Kaggle data ({len(y)} records) instead of local data ({len(y_local)} records)')
                        else:
                            X, y, feature_names = X_local, y_local, feature_names_local
                            self.stdout.write(
                                self.style.SUCCESS(f'✅ Local data processed: {len(y)} records, {X.shape[1]} features'))
                    else:
                        self.stdout.write(self.style.WARNING('⚠️ Not enough local data for model training'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Error processing local data: {str(e)}'))
                    traceback.print_exc()

            # Validate loaded data
            if X is None or y is None:
                self.stdout.write(self.style.ERROR('❌ Failed to load any usable data'))
                return None, None, None, None, None

            # Check for NaN values
            if np.isnan(X).any() or np.isnan(y).any():
                self.stdout.write(self.style.WARNING('⚠️ NaN values detected in data, replacing with zeros'))
                X = np.nan_to_num(X, 0)
                y = np.nan_to_num(y, 0)

            # Check for infinite values
            if not np.isfinite(X).all() or not np.isfinite(y).all():
                self.stdout.write(self.style.WARNING('⚠️ Infinite values detected in data, replacing with zeros'))
                X = np.nan_to_num(X, 0, posinf=0, neginf=0)
                y = np.nan_to_num(y, 0, posinf=0, neginf=0)

            # Split into train and test sets
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42
            )

            return X_train, X_test, y_train, y_test, feature_names

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Data loading error: {str(e)}'))
            traceback.print_exc()
            return None, None, None, None, None

    def prepare_kaggle_features(self, anime_df, rating_df):
        """Prepare features from Kaggle data"""
        try:
            # Merge anime and rating data
            df = rating_df.merge(anime_df, on='anime_id', how='left')

            # Handle missing values
            df['rating_y'] = df['rating_y'].fillna(0)
            df['members'] = df['members'].fillna(0)

            # Handle non-numeric data in episodes column
            df['episodes'] = pd.to_numeric(df['episodes'], errors='coerce').fillna(0)

            # Encode user and anime IDs
            user_encoder = LabelEncoder()
            anime_encoder = LabelEncoder()

            df['user_id_encoded'] = user_encoder.fit_transform(df['user_id'])
            df['anime_id_encoded'] = anime_encoder.fit_transform(df['anime_id'])

            # Create type feature
            df['type_encoded'] = df['type'].astype('category').cat.codes

            # Encode genre features - properly handle missing values
            df['genre'] = df['genre'].fillna('')
            genre_dummies = df['genre'].str.get_dummies(sep=',')
            top_genres = genre_dummies.sum().sort_values(ascending=False).head(10).index
            genre_dummies = genre_dummies[top_genres]

            # Prepare feature matrix
            features = [
                'user_id_encoded', 'anime_id_encoded', 'type_encoded',
                'episodes', 'members', 'rating_y'
            ]

            # Add genre features
            for genre in top_genres:
                features.append(f'genre_{genre}')
                df[f'genre_{genre}'] = genre_dummies[genre]

            # Aggregate user statistics
            user_stats = df.groupby('user_id').agg({
                'rating_x': ['count', 'mean', 'std']
            })
            user_stats.columns = ['user_rating_count', 'user_rating_mean', 'user_rating_std']
            user_stats = user_stats.reset_index()
            user_stats['user_rating_std'] = user_stats['user_rating_std'].fillna(0)

            # Merge user statistics
            df = df.merge(user_stats, on='user_id', how='left')
            features.extend(['user_rating_count', 'user_rating_mean', 'user_rating_std'])

            # Aggregate anime statistics
            anime_stats = df.groupby('anime_id').agg({
                'rating_x': ['count', 'mean', 'std']
            })
            anime_stats.columns = ['anime_rating_count', 'anime_rating_mean', 'anime_rating_std']
            anime_stats = anime_stats.reset_index()
            anime_stats['anime_rating_std'] = anime_stats['anime_rating_std'].fillna(0)

            # Merge anime statistics
            df = df.merge(anime_stats, on='anime_id', how='left')
            features.extend(['anime_rating_count', 'anime_rating_mean', 'anime_rating_std'])

            # Final feature matrix and target values
            X = df[features].values
            y = df['rating_x'].values

            # Standardize features
            scaler = StandardScaler()
            X = scaler.fit_transform(X)

            return X, y, features

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Kaggle feature preparation error: {str(e)}'))
            traceback.print_exc()
            return None, None, None

    def prepare_local_features(self):
        """Prepare features from local database"""
        try:
            # Check if we're running standalone
            if 'UserRating' not in globals() and 'UserRating' not in locals():
                self.stdout.write(self.style.WARNING("Running in standalone mode, can't access local database"))
                return None, None, None

            # Load rating data from database
            ratings = UserRating.objects.all().values('user_id', 'anime_id', 'rating')

            if len(ratings) < 100:
                self.stdout.write(self.style.WARNING(f"⚠️ Not enough local rating data, only {len(ratings)} records"))
                return None, None, None

            # Convert to DataFrame
            ratings_df = pd.DataFrame(ratings)

            # Get anime features
            animes = {}
            for anime in Anime.objects.all():
                animes[anime.id] = {
                    'popularity': anime.popularity or 0,
                    'rating_avg': anime.rating_avg or 0,
                    'rating_count': anime.rating_count or 0,
                    'type_id': anime.type_id or 0,
                    'favorite_count': anime.favorite_count or 0,
                    'view_count': anime.view_count or 0,
                    'is_completed': 1 if anime.is_completed else 0,
                    'is_featured': 1 if anime.is_featured else 0
                }

            # Create user features
            users = {}
            for user_id in ratings_df['user_id'].unique():
                user_ratings = ratings_df[ratings_df['user_id'] == user_id]
                users[user_id] = {
                    'rating_count': len(user_ratings),
                    'rating_mean': user_ratings['rating'].mean(),
                    'rating_std': user_ratings['rating'].std() if len(user_ratings) > 1 else 0
                }

            # Encode user and anime IDs
            user_encoder = LabelEncoder()
            anime_encoder = LabelEncoder()

            user_ids = ratings_df['user_id'].values
            anime_ids = ratings_df['anime_id'].values

            encoded_users = user_encoder.fit_transform(user_ids)
            encoded_animes = anime_encoder.fit_transform(anime_ids)

            # Build feature matrix
            X_data = []
            feature_names = [
                'user_encoded', 'user_rating_count', 'user_rating_mean', 'user_rating_std',
                'anime_encoded', 'popularity', 'rating_avg', 'rating_count', 'type_id',
                'favorite_count', 'view_count', 'is_completed', 'is_featured'
            ]

            for i, (user_id, anime_id) in enumerate(zip(user_ids, anime_ids)):
                user_features = [
                    encoded_users[i],
                    users[user_id]['rating_count'],
                    users[user_id]['rating_mean'],
                    users[user_id]['rating_std']
                ]

                anime_feature = [encoded_animes[i]]
                if anime_id in animes:
                    anime_data = animes[anime_id]
                    anime_feature.extend([
                        anime_data['popularity'],
                        anime_data['rating_avg'],
                        anime_data['rating_count'],
                        anime_data['type_id'],
                        anime_data['favorite_count'],
                        anime_data['view_count'],
                        anime_data['is_completed'],
                        anime_data['is_featured']
                    ])
                else:
                    anime_feature.extend([0, 0, 0, 0, 0, 0, 0, 0])

                X_data.append(user_features + anime_feature)

            # Convert to numpy array
            X = np.array(X_data)
            y = ratings_df['rating'].values

            # Standardize features
            scaler = StandardScaler()
            X = scaler.fit_transform(X)

            return X, y, feature_names

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Local feature preparation error: {str(e)}'))
            traceback.print_exc()
            return None, None, None

    def get_models(self, feature_names, input_dim):
        """Define models for comparison, with simplified GPU handling"""
        models = {
            'GBDT': GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            ),
            'XGBoost': xgb.XGBRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                reg_alpha=0.01,
                reg_lambda=1.0,
                random_state=42,
                # Remove tree_method and device parameters to use default handling
            ),
        }

        # Only add LightGBM if available
        if LIGHTGBM_AVAILABLE:
            lgb_params = {
                'n_estimators': 100,
                'learning_rate': 0.1,
                'max_depth': 5,
                'num_leaves': 31,
                'feature_fraction': 0.8,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'random_state': 42,
                # GPU parameters removed - use default CPU mode for compatibility
            }

            models['LightGBM'] = lgb.LGBMRegressor(**lgb_params)

        # If TensorFlow is available, add neural network
        if TENSORFLOW_AVAILABLE:
            # TensorFlow will automatically use GPU if available
            models['NeuralNetwork'] = self.create_nn_model(input_dim)

        return models

    def create_nn_model(self, input_dim):
        """Create neural network model with explicit input dimension and better initialization"""
        if not TENSORFLOW_AVAILABLE:
            return None

        try:
            # Explicitly set the random seed for reproducibility
            import tensorflow as tf
            tf.random.set_seed(42)

            # Create a neural network using Input layer as first layer
            inputs = tf.keras.Input(shape=(input_dim,))
            x = tf.keras.layers.Dense(64, activation='relu', kernel_initializer='he_normal')(inputs)
            x = tf.keras.layers.BatchNormalization()(x)
            x = tf.keras.layers.Dropout(0.3)(x)
            x = tf.keras.layers.Dense(32, activation='relu', kernel_initializer='he_normal')(x)
            x = tf.keras.layers.BatchNormalization()(x)
            x = tf.keras.layers.Dropout(0.2)(x)
            x = tf.keras.layers.Dense(16, activation='relu', kernel_initializer='he_normal')(x)
            outputs = tf.keras.layers.Dense(1, kernel_initializer='normal')(x)

            model = tf.keras.Model(inputs=inputs, outputs=outputs)

            # Use reduced verbosity during compilation
            original_stdout = sys.stdout
            sys.stdout = open(os.devnull, 'w')
            try:
                model.compile(
                    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
                    loss='mse',
                    metrics=['mae']
                )
            finally:
                sys.stdout.close()
                sys.stdout = original_stdout

            self.stdout.write(f"✅ Neural network model created with input dim: {input_dim}")
            return model

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating neural network model: {str(e)}"))
            traceback.print_exc()
            return None

    def run_experiment(self, models, X_train, X_test, y_train, y_test):
        """Train and evaluate models - with improved error handling and device management"""
        results = {}

        # Iterate through all models
        for name, model in models.items():
            try:
                self.stdout.write(f'🧪 Training model: {name}...')

                # Record start time and memory
                start_time = time.time()
                start_memory = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)  # MB

                # Train model
                if name == 'NeuralNetwork' and TENSORFLOW_AVAILABLE:
                    # Capture TensorFlow warnings and errors
                    import tensorflow as tf
                    old_verbosity = tf.compat.v1.logging.get_verbosity()
                    tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)

                    # Special handling for neural network
                    early_stopping = tf.keras.callbacks.EarlyStopping(
                        monitor='val_loss', patience=5, restore_best_weights=True
                    )

                    model.fit(
                        X_train, y_train,
                        epochs=50,
                        batch_size=256,
                        validation_split=0.1,
                        callbacks=[early_stopping],
                        verbose=0
                    )

                    # Restore verbosity
                    tf.compat.v1.logging.set_verbosity(old_verbosity)

                elif name == 'LightGBM' and LIGHTGBM_AVAILABLE:
                    # Create dataset with feature names
                    train_data = lgb.Dataset(X_train, label=y_train)

                    # Use native LightGBM API for training
                    params = {
                        'objective': 'regression',
                        'metric': 'rmse',
                        'learning_rate': 0.1,
                        'num_leaves': 31,
                        'max_depth': 5,
                        'feature_fraction': 0.8,
                        'bagging_fraction': 0.8,
                        'bagging_freq': 5,
                        'verbose': -1
                    }

                    # Train model using native API
                    lgb_model = lgb.train(
                        params,
                        train_data,
                        num_boost_round=100
                    )

                    # Replace the scikit-learn model with the native model
                    models[name] = lgb_model
                else:
                    # Standard scikit-learn compatible training for all other models
                    model.fit(X_train, y_train)

                # Record training time and memory
                train_time = time.time() - start_time
                train_memory = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024) - start_memory

                # Record prediction start time
                pred_start_time = time.time()

                # Predict
                if name == 'NeuralNetwork' and TENSORFLOW_AVAILABLE:
                    y_pred = model.predict(X_test, verbose=0).flatten()
                elif name == 'LightGBM' and LIGHTGBM_AVAILABLE and hasattr(models[name], 'predict'):
                    # Use native predict for LightGBM
                    y_pred = models[name].predict(X_test)
                else:
                    # Standard prediction for all scikit-learn compatible models
                    y_pred = model.predict(X_test)

                # Record prediction time
                pred_time = time.time() - pred_start_time

                # Calculate evaluation metrics
                rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                mae = mean_absolute_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)

                # Store results - limit prediction data to a sample for visualization
                pred_sample = y_pred[:100] if len(y_pred) > 100 else y_pred

                results[name] = {
                    'rmse': rmse,
                    'mae': mae,
                    'r2': r2,
                    'train_time': train_time,
                    'pred_time': pred_time,
                    'memory_mb': train_memory,
                    'y_pred': pred_sample  # Store a sample for visualization
                }

                self.stdout.write(f'  - RMSE: {rmse:.4f}')
                self.stdout.write(f'  - MAE: {mae:.4f}')
                self.stdout.write(f'  - R²: {r2:.4f}')
                self.stdout.write(f'  - Training time: {train_time:.2f} seconds')
                self.stdout.write(f'  - Prediction time: {pred_time:.4f} seconds')
                self.stdout.write(f'  - Memory usage: {train_memory:.2f}MB')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error training/evaluating model {name}: {str(e)}"))
                traceback.print_exc()
                # Add fallback metrics for failed models
                results[name] = {
                    'rmse': 999.0,
                    'mae': 999.0,
                    'r2': 0.0,
                    'train_time': 999.0,
                    'pred_time': 999.0,
                    'memory_mb': 999.0,
                    'y_pred': np.full(min(100, len(y_test)), np.mean(y_train))
                }

            finally:
                # Force garbage collection to release memory
                gc.collect()

        return results

    def visualize_performance_trends(self, results, output_dir):
        """
        Generate performance trend visualizations

        Args:
            results: Dictionary containing model evaluation results
            output_dir: Output directory
        """
        # Clean results data (remove prediction arrays)
        cleaned_results = {}
        for model_name, metrics in results.items():
            cleaned_results[model_name] = {k: v for k, v in metrics.items() if k != 'y_pred'}

        # Convert to DataFrame
        df = pd.DataFrame(cleaned_results).T

        # =========== 1. Performance radar charts ===========
        plt.figure(figsize=(14, 12))

        # Prepare radar chart data by normalizing all metrics
        # Values of 1 always represent best performance
        normalized_df = pd.DataFrame(index=df.index)

        # For metrics where lower is better, invert the normalization
        for metric in ['rmse', 'mae', 'train_time', 'pred_time', 'memory_mb']:
            max_val = df[metric].max()
            min_val = df[metric].min()
            if max_val > min_val:
                normalized_df[metric] = 1 - (df[metric] - min_val) / (max_val - min_val)
            else:
                normalized_df[metric] = 1.0

        # For R² (higher is better), normalize directly
        if df['r2'].max() > df['r2'].min():
            normalized_df['r2'] = (df['r2'] - df['r2'].min()) / (df['r2'].max() - df['r2'].min())
        else:
            normalized_df['r2'] = 1.0

        # Define metric categories and labels
        metrics_categories = {
            'Prediction Accuracy': ['rmse', 'mae', 'r2'],
            'Computational Efficiency': ['train_time', 'pred_time'],
            'Resource Usage': ['memory_mb']
        }

        metric_labels = {
            'rmse': 'RMSE\nAccuracy',
            'mae': 'MAE\nRobustness',
            'r2': 'R²\nExplanatory Power',
            'train_time': 'Training Time',
            'pred_time': 'Prediction Time',
            'memory_mb': 'Memory Usage'
        }

        # Create subplots for each category
        for i, (category, metrics) in enumerate(metrics_categories.items()):
            ax = plt.subplot(2, 2, i + 1, polar=True)

            # Set radar chart parameters
            angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
            angles += angles[:1]  # Close the polygon

            # Set axis labels
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels([self.translate(metric_labels[m]) for m in metrics])

            # Plot each model's performance curve
            for j, model in enumerate(normalized_df.index):
                values = [normalized_df.loc[model, m] for m in metrics]
                values += values[:1]  # Close the polygon

                ax.plot(angles, values, 'o-', linewidth=2, label=model, alpha=0.8)
                ax.fill(angles, values, alpha=0.1)

            # Set title and grid
            ax.set_title(self.translate(f'{category} Radar Chart'), fontsize=14, fontweight='bold')
            ax.grid(True, linestyle='--', alpha=0.7)

            # Only show legend in first subplot
            if i == 0:
                ax.legend(loc='upper right', bbox_to_anchor=(0.3, 0.1))

        # Create comprehensive performance radar chart
        ax = plt.subplot(2, 2, 4, polar=True)
        all_metrics = list(normalized_df.columns)

        # Set radar chart parameters
        angles = np.linspace(0, 2 * np.pi, len(all_metrics), endpoint=False).tolist()
        angles += angles[:1]  # Close the polygon

        # Set axis labels
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels([self.translate(metric_labels.get(m, m)) for m in all_metrics])

        # Plot each model's performance curve
        for j, model in enumerate(normalized_df.index):
            values = [normalized_df.loc[model, m] for m in all_metrics]
            values += values[:1]  # Close the polygon

            ax.plot(angles, values, 'o-', linewidth=2, label=model, alpha=0.8)
            ax.fill(angles, values, alpha=0.1)

        # Set title and grid
        ax.set_title(self.translate('Full Performance Radar Chart'), fontsize=14, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.7)

        # Add overall title and explanation
        plt.suptitle(self.translate('Multidimensional Model Performance Analysis'), fontsize=16, fontweight='bold')

        plt.figtext(0.5, 0.02,
                    self.translate('Note: All metrics normalized to 0-1 range, with 1 representing best performance.\n'
                                   'For metrics like RMSE where "lower is better", values have been inverted so that higher values represent better performance.'),
                    ha='center', fontsize=10, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))

        # FIXED: Use subplots_adjust instead of tight_layout
        plt.subplots_adjust(top=0.9, bottom=0.1, left=0.1, right=0.9)

        # Save image
        radar_path = os.path.join(output_dir, 'performance_radar_analysis.png')
        plt.savefig(radar_path, dpi=300, bbox_inches='tight')
        plt.close()

        # =========== 2. Normalized performance line chart ===========
        plt.figure(figsize=(14, 8))

        # Prepare data
        metrics_to_plot = ['rmse', 'mae', 'r2', 'train_time', 'pred_time', 'memory_mb']
        metric_names = {
            'rmse': self.translate('RMSE\nAccuracy'),
            'mae': self.translate('MAE\nRobustness'),
            'r2': self.translate('R²\nExplanatory Power'),
            'train_time': self.translate('Training Time\nEfficiency'),
            'pred_time': self.translate('Prediction Time\nEfficiency'),
            'memory_mb': self.translate('Memory\nEfficiency')
        }

        # Set x-axis positions
        x = np.arange(len(metrics_to_plot))

        # Plot line for each model
        for i, model in enumerate(normalized_df.index):
            model_values = [normalized_df.loc[model, m] for m in metrics_to_plot]
            plt.plot(x, model_values, 'o-', linewidth=2, label=model, markersize=8)

        # Set x-axis labels and grid
        plt.xticks(x, [metric_names[m] for m in metrics_to_plot])
        plt.grid(True, linestyle='--', alpha=0.7)

        # Add y-axis label and title
        plt.ylabel(self.translate('Normalized Performance (Higher is Better)'), fontsize=12)
        plt.title(self.translate('Unified Model Performance Comparison'), fontsize=16, fontweight='bold')

        # Add legend
        plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=len(normalized_df.index), fontsize=10)

        # Add explanation text
        plt.figtext(0.5, 0.01,
                    self.translate('Note: All metrics normalized to 0-1 range, with 1 representing best performance.\n'
                                   'For metrics like RMSE where "lower is better", values have been inverted for consistent "higher is better" interpretation.'),
                    ha='center', fontsize=10, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))

        # FIXED: Use subplots_adjust instead of tight_layout
        plt.subplots_adjust(top=0.9, bottom=0.2, left=0.1, right=0.9)

        # Save image
        line_path = os.path.join(output_dir, 'normalized_performance_comparison.png')
        plt.savefig(line_path, dpi=300, bbox_inches='tight')
        plt.close()

        # =========== 3. Model ranking heatmap ===========
        plt.figure(figsize=(14, 8))

        # Calculate ranking for each metric
        ranking_df = pd.DataFrame(index=df.index)

        # For metrics where lower is better, rank in ascending order
        for metric in ['rmse', 'mae', 'train_time', 'pred_time', 'memory_mb']:
            ranking_df[metric] = df[metric].rank()

        # For R² (higher is better), rank in descending order
        ranking_df['r2'] = df['r2'].rank(ascending=False)

        # Calculate average rank
        ranking_df['avg_rank'] = ranking_df.mean(axis=1)

        # Sort by average rank
        ranking_df = ranking_df.sort_values('avg_rank')

        # Plot heatmap
        # Create separate figure and axes to handle colorbar placement
        fig, ax = plt.subplots(figsize=(14, 8))

        # Plot heatmap with separate colorbar
        heatmap = sns.heatmap(ranking_df.drop(columns=['avg_rank']), annot=True, cmap='YlGnBu_r',
                              fmt='.1f', linewidths=0.5, cbar_kws={'label': self.translate('Rank (1 is best)')}, ax=ax)

        # Add average rank
        for i, model in enumerate(ranking_df.index):
            ax.text(len(ranking_df.columns) - 0.5, i + 0.5, f"Avg: {ranking_df.loc[model, 'avg_rank']:.2f}",
                    ha='center', va='center', fontsize=10, fontweight='bold',
                    bbox=dict(facecolor='white', edgecolor='gray', alpha=0.8, boxstyle='round,pad=0.2'))

        ax.set_title(self.translate('Model Performance Ranking Comparison'), fontsize=16, fontweight='bold')

        # Adjust subplots instead of tight_layout
        plt.subplots_adjust(bottom=0.15, top=0.9, left=0.1, right=0.9)

        # Save image
        rank_path = os.path.join(output_dir, 'model_performance_ranking.png')
        plt.savefig(rank_path, dpi=300, bbox_inches='tight')
        plt.close()

    def visualize_comparison(self, results, output_dir):
        """Generate model performance comparison visualizations with fixed layouts"""
        # Clean results by removing prediction arrays
        cleaned_results = {}
        for model_name, metrics in results.items():
            cleaned_results[model_name] = {k: v for k, v in metrics.items() if k != 'y_pred'}

        # Convert to DataFrame for easier plotting
        df = pd.DataFrame(cleaned_results).T

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # =========== 1. Accuracy metrics comparison chart ===========
        try:
            # Create figure and axes explicitly for better control
            fig_acc, axes = plt.subplots(2, 2, figsize=(12, 10))

            # RMSE comparison (lower is better)
            sorted_models = df.sort_values('rmse').index
            bars = sns.barplot(x=sorted_models, y=df.loc[sorted_models, 'rmse'], ax=axes[0, 0],
                               palette="Blues_r", hue=sorted_models, legend=False)
            axes[0, 0].set_title(self.translate('RMSE\nLower is Better'), fontsize=13, fontweight='bold')
            axes[0, 0].set_ylabel(self.translate('Error Value'))
            axes[0, 0].set_xlabel(self.translate('Model'))

            # Add value labels
            for i, bar in enumerate(bars.patches):
                axes[0, 0].text(
                    bar.get_x() + bar.get_width() / 2.,
                    bar.get_height() + 0.005,
                    f'{bar.get_height():.4f}',
                    ha='center', va='bottom', fontsize=9, rotation=0
                )

            # R² comparison (higher is better)
            sorted_models = df.sort_values('r2', ascending=False).index
            bars = sns.barplot(x=sorted_models, y=df.loc[sorted_models, 'r2'], ax=axes[0, 1],
                               palette="Greens", hue=sorted_models, legend=False)
            axes[0, 1].set_title(self.translate('R²\nHigher is Better'), fontsize=13, fontweight='bold')
            axes[0, 1].set_ylabel(self.translate('R² Value'))
            axes[0, 1].set_xlabel(self.translate('Model'))

            # Add value labels
            for i, bar in enumerate(bars.patches):
                axes[0, 1].text(
                    bar.get_x() + bar.get_width() / 2.,
                    bar.get_height() - 0.05,
                    f'{bar.get_height():.4f}',
                    ha='center', va='bottom', fontsize=9, color='white', rotation=0
                )

            # Create error comparison chart (RMSE vs MAE)
            width = 0.35
            x = np.arange(len(df.index))

            # Normalize error values for better comparison
            max_rmse = df['rmse'].max()
            max_mae = df['mae'].max()
            ratio = max_rmse / max_mae if max_mae > 0 else 1

            axes[1, 0].bar(x - width / 2, df['rmse'], width, label='RMSE', color='#5975a4', alpha=0.8)
            axes[1, 0].bar(x + width / 2, df['mae'] * ratio, width, label='MAE (normalized)', color='#5f9e6e',
                           alpha=0.8)

            # Add MAE original value labels
            for i, v in enumerate(df['mae']):
                axes[1, 0].text(i + width / 2, v * ratio + 0.01, f'{v:.4f}', ha='center', fontsize=9)

            # Add RMSE value labels
            for i, v in enumerate(df['rmse']):
                axes[1, 0].text(i - width / 2, v + 0.01, f'{v:.4f}', ha='center', fontsize=9)

            axes[1, 0].set_xticks(x)
            axes[1, 0].set_xticklabels(df.index)
            axes[1, 0].set_title(self.translate('RMSE vs MAE Comparison'), fontsize=14, fontweight='bold')
            axes[1, 0].set_ylabel(self.translate('Error Value'))
            axes[1, 0].set_xlabel(self.translate('Model'))
            axes[1, 0].legend(loc='upper right')

            # Leave the fourth subplot empty for now or use it for a summary
            axes[1, 1].axis('off')

            # Add explanation text as a textbox in the empty subplot
            explanation_text = self.translate(
                'Note: RMSE is more sensitive to outliers, while MAE gives equal weight to all errors.\n'
                'Both are lower-is-better metrics, reflecting the average deviation between predicted and actual values.')
            axes[1, 1].text(0.5, 0.5, explanation_text,
                            ha='center', va='center', fontsize=10,
                            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'),
                            wrap=True, transform=axes[1, 1].transAxes)

            # Add super title
            fig_acc.suptitle(self.translate('Model Prediction Accuracy Evaluation'), fontsize=16, fontweight='bold',
                             y=0.98)

            # Adjust layout
            plt.tight_layout(rect=[0, 0, 1, 0.95])

            # Save image
            acc_path = os.path.join(output_dir, 'accuracy_metrics_comparison.png')
            plt.savefig(acc_path, dpi=300, bbox_inches='tight')
            plt.close(fig_acc)

            self.stdout.write(self.style.SUCCESS(f'✅ Generated accuracy metrics comparison chart: {acc_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to generate accuracy metrics chart: {str(e)}'))
            traceback.print_exc()

        # =========== 2. Performance metrics comparison chart ===========
        try:
            fig_perf = plt.figure(figsize=(15, 10))

            # Create manual grid
            gs = plt.GridSpec(2, 3, figure=fig_perf)
            ax1 = fig_perf.add_subplot(gs[0, :2])  # Top left, spanning 2 columns
            ax2 = fig_perf.add_subplot(gs[0, 2])  # Top right
            ax3 = fig_perf.add_subplot(gs[1, :], projection='polar')  # Bottom, spanning all columns

            # Training and prediction time comparison
            models = df.index
            x = np.arange(len(models))
            width = 0.35

            # Training and prediction times
            training_times = df['train_time']
            prediction_times = df['pred_time']

            # Plot bar chart
            ax1.bar(x - width / 2, training_times, width, label=self.translate('Training Time'), color='#d65f5f',
                    alpha=0.7)
            ax1.bar(x + width / 2, prediction_times, width, label=self.translate('Prediction Time'), color='#ee8866',
                    alpha=0.7)

            # Add value labels with safety checks
            for i, v in enumerate(training_times):
                ax1.text(i - width / 2, v + 0.2, f'{v:.2f}s', ha='center', va='bottom', fontsize=9, rotation=0)

            for i, v in enumerate(prediction_times):
                ax1.text(i + width / 2, v + 0.01, f'{v:.4f}s', ha='center', va='bottom', fontsize=9, rotation=0)

            ax1.set_ylabel(self.translate('Time (seconds)'), fontsize=12)
            ax1.set_xticks(x)
            ax1.set_xticklabels(models, rotation=0)
            ax1.set_title(self.translate('Training vs Prediction Time'), fontsize=14, fontweight='bold')
            # Use symlog scale for better visualization with wide ranges
            if max(training_times) / min(training_times) > 100 or max(prediction_times) / min(prediction_times) > 100:
                ax1.set_yscale('symlog')
            ax1.legend()

            # Memory usage comparison
            sorted_models = df.sort_values('memory_mb').index
            bars = sns.barplot(x=sorted_models, y=df.loc[sorted_models, 'memory_mb'], ax=ax2,
                               palette='Reds', hue=sorted_models, legend=False)
            ax2.set_title(self.translate('Memory Usage\nLower is Better'), fontsize=13, fontweight='bold')
            ax2.set_ylabel(self.translate('Memory Usage (MB)'))
            ax2.set_xlabel(self.translate('Model'))

            # Add value labels
            for i, bar in enumerate(bars.patches):
                ax2.text(
                    bar.get_x() + bar.get_width() / 2.,
                    bar.get_height() + 1,
                    f'{bar.get_height():.1f}',
                    ha='center', va='bottom', fontsize=9
                )

            # Create radar chart comparing all performance metrics
            categories = [
                self.translate('RMSE\n(Lower is Better)'),
                self.translate('MAE\n(Lower is Better)'),
                self.translate('R²\n(Higher is Better)'),
                self.translate('Training Time\n(Lower is Better)'),
                self.translate('Prediction Time\n(Lower is Better)'),
                self.translate('Memory Usage\n(Lower is Better)')
            ]
            N = len(categories)

            # Create radar chart coordinates
            angles = [n / float(N) * 2 * np.pi for n in range(N)]
            angles += angles[:1]  # Close the polygon

            # Initialize radar chart
            ax3.set_theta_offset(np.pi / 2)
            ax3.set_theta_direction(-1)
            ax3.set_rlabel_position(0)
            ax3.set_xticks(angles[:-1])
            ax3.set_xticklabels(categories, fontsize=10)

            # Plot each model's radar chart
            colors = plt.cm.tab10(np.linspace(0, 1, len(models)))

            # Normalize all metrics to 0-1 range, where 1 is always best
            normalized_df = pd.DataFrame(index=df.index)

            # For metrics where lower is better, invert the normalization
            for metric in ['rmse', 'mae', 'train_time', 'pred_time', 'memory_mb']:
                max_val = df[metric].max()
                min_val = df[metric].min()
                if max_val > min_val:
                    normalized_df[metric] = 1 - (df[metric] - min_val) / (max_val - min_val)
                else:
                    normalized_df[metric] = 1.0

            # For R² (higher is better), normalize directly
            if df['r2'].max() > df['r2'].min():
                normalized_df['r2'] = (df['r2'] - df['r2'].min()) / (df['r2'].max() - df['r2'].min())
            else:
                normalized_df['r2'] = 1.0

            # Plot radar chart
            for i, model in enumerate(models):
                values = [
                    normalized_df.loc[model, 'rmse'],
                    normalized_df.loc[model, 'mae'],
                    normalized_df.loc[model, 'r2'],
                    normalized_df.loc[model, 'train_time'],
                    normalized_df.loc[model, 'pred_time'],
                    normalized_df.loc[model, 'memory_mb']
                ]
                values += values[:1]  # Close the polygon

                ax3.plot(angles, values, linewidth=2, linestyle='-', label=model, color=colors[i])
                ax3.fill(angles, values, alpha=0.1, color=colors[i])

            # Set radar chart scale and title
            ax3.set_ylim(0, 1.1)
            ax3.set_title(self.translate('Model Multidimensional Performance Comparison (Normalized)'), fontsize=14,
                          fontweight='bold')
            ax3.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))

            # Add overall title
            fig_perf.suptitle(self.translate('Model Performance & Computational Resource Analysis'), fontsize=16,
                              fontweight='bold', y=0.98)

            # Add explanation text
            plt.figtext(0.5, 0.01,
                        self.translate(
                            'Note: In the radar chart, all metrics are normalized to 0-1 range, with 1 representing best performance.\n'
                            'For metrics like RMSE where "lower is better", values have been inverted to maintain the "higher is better" standard.'),
                        ha='center', fontsize=10, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))

            # Adjust layout
            plt.tight_layout(rect=[0, 0.05, 1, 0.95])

            # Save image
            perf_path = os.path.join(output_dir, 'performance_metrics_comparison.png')
            plt.savefig(perf_path, dpi=300, bbox_inches='tight')
            plt.close(fig_perf)

            self.stdout.write(self.style.SUCCESS(f'✅ Generated performance metrics comparison chart: {perf_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to generate performance metrics chart: {str(e)}'))
            traceback.print_exc()

        # Add more chart code here...
        # The other visualization methods work in a similar way

    def visualize_feature_importance(self, models, feature_names, output_dir):
        """
        Visualize feature importance for tree-based models

        Args:
            models: Dictionary of models
            feature_names: List of feature names
            output_dir: Output directory
        """
        # Only process models with feature_importances_ attribute
        tree_models = {}
        for name, model in models.items():
            if hasattr(model, 'feature_importances_'):
                tree_models[name] = model
            elif name == 'LightGBM' and hasattr(model, 'feature_importance'):
                tree_models[name] = model

        if not tree_models:
            print('No tree models available for feature importance visualization')
            return

        # Extract feature importance for all models
        importances_dict = {}

        for name, model in tree_models.items():
            # Get feature importance
            if name == 'LightGBM' and hasattr(model, 'feature_importance'):
                importances = model.feature_importance(importance_type='gain')
            else:
                importances = model.feature_importances_

            # Ensure feature names match importance count
            if len(importances) == len(feature_names):
                feat_imp = dict(zip(feature_names, importances))
            else:
                print(
                    f'Feature count mismatch: model features {len(importances)}, provided feature names {len(feature_names)}')
                feat_imp = dict(zip([f'Feature{i}' for i in range(len(importances))], importances))

            importances_dict[name] = feat_imp

        # Find all top important features across models
        all_features = set()
        for model_imp in importances_dict.values():
            # Sort by importance, get top 10
            top_features = sorted(model_imp.items(), key=lambda x: x[1], reverse=True)[:10]
            all_features.update([f[0] for f in top_features])

        # Limit to 15 features max
        if len(all_features) > 15:
            # Calculate average importance for each feature
            avg_importance = {}
            for feature in all_features:
                values = [imp.get(feature, 0) for imp in importances_dict.values()]
                avg_importance[feature] = sum(values) / len(values)

            # Select top 15 features by average importance
            all_features = sorted(avg_importance.items(), key=lambda x: x[1], reverse=True)[:15]
            all_features = [f[0] for f in all_features]
        else:
            # Convert set to list to maintain order
            all_features = list(all_features)

        # Create feature importance heatmap
        plt.figure(figsize=(14, 10))

        # Prepare heatmap data
        heatmap_data = []
        for feature in all_features:
            row = []
            for model in tree_models:
                # Get importance for this feature in this model
                importance = importances_dict[model].get(feature, 0)
                row.append(importance)
            heatmap_data.append(row)

        # Convert to DataFrame
        heatmap_df = pd.DataFrame(heatmap_data, index=all_features, columns=tree_models.keys())

        # Normalize each model's feature importance
        for model in heatmap_df.columns:
            max_val = heatmap_df[model].max()
            if max_val > 0:
                heatmap_df[model] = heatmap_df[model] / max_val

        # Create figure and axis explicitly
        fig, ax = plt.subplots(figsize=(14, 10))

        # Create heatmap
        cmap = LinearSegmentedColormap.from_list('custom_cmap', ['#ffffff', '#4878d0', '#3c9d6f', '#ee8866', '#d65f5f'])
        sns.heatmap(heatmap_df, cmap=cmap, annot=True, fmt='.2f', linewidths=0.5, ax=ax,
                    cbar_kws={'label': self.translate('Normalized Feature Importance')})

        ax.set_title(self.translate('Feature Importance Comparison Across Models'), fontsize=16, fontweight='bold')
        ax.set_ylabel(self.translate('Feature'), fontsize=14)
        ax.set_xlabel(self.translate('Model'), fontsize=14)

        # Add explanation text
        plt.figtext(0.5, 0.01,
                    self.translate(
                        'Note: Values are normalized feature importance scores (0-1) within each model, with darker colors indicating higher importance.\n'
                        'The features shown are the union of the most important features across all models.'),
                    ha='center', fontsize=10, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))

        # FIXED: Use subplots_adjust instead of tight_layout
        plt.subplots_adjust(bottom=0.15, top=0.9, left=0.1, right=0.9)

        # Save image
        heatmap_path = os.path.join(output_dir, 'feature_importance_heatmap.png')
        plt.savefig(heatmap_path, dpi=300, bbox_inches='tight')
        plt.close()

        # Create individual feature importance bar charts for each model
        for model_name, importances in importances_dict.items():
            plt.figure(figsize=(12, 8))

            # Convert feature importance to sortable list
            feat_imp_list = [(feat, imp) for feat, imp in importances.items()]
            # Sort by importance
            feat_imp_list.sort(key=lambda x: x[1], reverse=True)

            # Only show top 15 features
            top_n = min(15, len(feat_imp_list))
            features = [x[0] for x in feat_imp_list[:top_n]]
            values = [x[1] for x in feat_imp_list[:top_n]]

            # Plot bar chart
            bars = plt.barh(range(len(features)), values, align='center', color='#4878d0', alpha=0.8)
            plt.yticks(range(len(features)), features)
            plt.gca().invert_yaxis()  # Put most important feature on top

            # Add value labels
            for i, v in enumerate(values):
                plt.text(v + 0.01 * max(values), i, f'{v:.4f}', va='center', fontsize=9)

            plt.title(self.translate(f'{model_name} Model - Feature Importance Analysis'), fontsize=16,
                      fontweight='bold')
            plt.xlabel(self.translate('Feature Importance'), fontsize=14)
            plt.ylabel(self.translate('Feature'), fontsize=14)
            plt.grid(axis='x', linestyle='--', alpha=0.7)

            # Add explanation text
            plt.figtext(0.5, 0.01,
                        self.translate(f'Note: This chart shows the top {top_n} features in the {model_name} model.\n'
                                       'Higher importance values indicate features with greater influence on model predictions.'),
                        ha='center', fontsize=10, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))

            # FIXED: Use subplots_adjust instead of tight_layout
            plt.subplots_adjust(bottom=0.15, top=0.9, left=0.3, right=0.9)

            # Save image
            model_imp_path = os.path.join(output_dir, f'{model_name}_feature_importance.png')
            plt.savefig(model_imp_path, dpi=300, bbox_inches='tight')
            plt.close()

    def visualize_prediction_distribution(self, models, X_test, y_test, output_dir):
        """
        Visualize prediction distribution

        Args:
            models: Dictionary of models
            X_test: Test features
            y_test: Test labels
            output_dir: Output directory
        """
        # Get predictions for each model
        predictions = {}
        for name, model in models.items():
            try:
                if name == 'NeuralNetwork' and TENSORFLOW_AVAILABLE:
                    pred = model.predict(X_test).flatten()
                elif name == 'LightGBM' and hasattr(model, 'predict'):
                    pred = model.predict(X_test)
                else:
                    pred = model.predict(X_test)
                predictions[name] = pred
            except Exception as e:
                print(f'Error getting predictions for model {name}: {str(e)}')
                continue

        if not predictions:
            print('No predictions available for visualization')
            return

        # =========== 1. Prediction distribution histogram ===========
        plt.figure(figsize=(14, 10))

        # Calculate actual value statistics
        actual_mean = np.mean(y_test)
        actual_median = np.median(y_test)
        actual_std = np.std(y_test)

        # Plot actual value distribution
        plt.subplot(211)
        sns.histplot(y_test, kde=True, stat="density", alpha=0.4, color='gray', label=self.translate('Actual Values'))
        plt.axvline(actual_mean, color='gray', linestyle='--', alpha=0.8,
                    label=f'{self.translate("Actual Mean")}={actual_mean:.2f}')

        # Set gradient colors
        colors = plt.cm.rainbow(np.linspace(0, 1, len(predictions)))

        # Plot predicted distribution for each model
        for i, (name, y_pred) in enumerate(predictions.items()):
            sns.histplot(y_pred, kde=True, stat="density", alpha=0.4, color=colors[i],
                         label=f'{name} {self.translate("Predictions")}')

            # Calculate statistics
            pred_mean = np.mean(y_pred)
            pred_median = np.median(y_pred)
            pred_std = np.std(y_pred)

            # Plot mean line
            plt.axvline(pred_mean, color=colors[i], linestyle='--', alpha=0.8,
                        label=f'{name} {self.translate("Mean")}={pred_mean:.2f}')

        plt.title(self.translate('Model Prediction vs Actual Distribution Comparison'), fontsize=15, fontweight='bold')
        plt.xlabel(self.translate('Value'), fontsize=12)
        plt.ylabel(self.translate('Density'), fontsize=12)
        plt.legend(loc='best', fontsize=10)

        # =========== 2. Prediction error boxplot ===========
        plt.subplot(212)

        # Calculate errors for each model
        error_data = []
        model_names = []

        for name, y_pred in predictions.items():
            # Calculate errors
            errors = y_test - y_pred
            error_data.append(errors)
            model_names.append(name)

        # Create boxplot
        box = plt.boxplot(error_data, patch_artist=True, labels=model_names,
                          showmeans=True, meanline=True)

        # Set boxplot colors
        for i, patch in enumerate(box['boxes']):
            patch.set_facecolor(colors[i])
            patch.set_alpha(0.7)

        # Add zero line (no error)
        plt.axhline(y=0, color='green', linestyle='-', alpha=0.7)

        # Calculate error statistics for each model
        for i, (name, y_pred) in enumerate(predictions.items()):
            errors = y_test - y_pred
            abs_errors = np.abs(errors)

            # Calculate statistics
            mean_error = np.mean(errors)
            median_error = np.median(errors)
            mean_abs_error = np.mean(abs_errors)
            std_error = np.std(errors)

            # Add statistics below the boxplot
            plt.text(i + 1, plt.ylim()[0] + (plt.ylim()[1] - plt.ylim()[0]) * 0.05,
                     f'{self.translate("Mean Error")}={mean_error:.3f}\nMAE={mean_abs_error:.3f}\n{self.translate("Std")}={std_error:.3f}',
                     ha='center', fontsize=8, bbox=dict(facecolor='white', alpha=0.7))

        plt.title(self.translate('Model Prediction Error Distribution Analysis'), fontsize=15, fontweight='bold')
        plt.ylabel(self.translate('Prediction Error (Actual - Predicted)'), fontsize=12)
        plt.xlabel(self.translate('Model'), fontsize=12)
        plt.grid(axis='y', linestyle='--', alpha=0.7)

        # Add explanation
        plt.figtext(0.5, 0.01,
                    self.translate(
                        'Note: The top chart compares prediction distributions with actual value distribution. The bottom chart shows error distributions.\n'
                        'Errors closer to zero indicate more accurate predictions. More concentrated distributions indicate more consistent predictions.'),
                    ha='center', fontsize=10, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))

        # FIXED: Use subplots_adjust instead of tight_layout
        plt.subplots_adjust(bottom=0.15, top=0.95, left=0.1, right=0.9, hspace=0.3)

        # Save image
        dist_path = os.path.join(output_dir, 'prediction_distribution_analysis.png')
        plt.savefig(dist_path, dpi=300, bbox_inches='tight')
        plt.close()

        # =========== 3. Q-Q plot analysis ===========
        plt.figure(figsize=(15, 10))

        # Create Q-Q plot for each model
        for i, (name, y_pred) in enumerate(predictions.items()):
            plt.subplot(2, 3, i + 1)

            # Calculate quantiles
            quantiles = np.arange(0, 101, 5)
            p_quantiles = np.percentile(y_pred, quantiles)
            a_quantiles = np.percentile(y_test, quantiles)

            # Plot Q-Q plot
            plt.scatter(a_quantiles, p_quantiles, alpha=0.8, s=50)

            # Add ideal line
            min_val = min(np.min(a_quantiles), np.min(p_quantiles))
            max_val = max(np.max(a_quantiles), np.max(p_quantiles))
            plt.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.8)

            # Calculate Q-Q plot RMSE
            qq_rmse = np.sqrt(np.mean((a_quantiles - p_quantiles) ** 2))

            plt.title(f'{name}\nQQ-RMSE={qq_rmse:.4f}', fontsize=12, fontweight='bold')
            plt.xlabel(self.translate('Actual Quantiles'), fontsize=10)
            plt.ylabel(self.translate('Predicted Quantiles'), fontsize=10)
            plt.grid(True, linestyle='--', alpha=0.7)

            # Analyze prediction errors in different value ranges
            low_idx = y_test < np.percentile(y_test, 33)
            mid_idx = (y_test >= np.percentile(y_test, 33)) & (y_test < np.percentile(y_test, 66))
            high_idx = y_test >= np.percentile(y_test, 66)

            low_rmse = np.sqrt(np.mean((y_test[low_idx] - y_pred[low_idx]) ** 2))
            mid_rmse = np.sqrt(np.mean((y_test[mid_idx] - y_pred[mid_idx]) ** 2))
            high_rmse = np.sqrt(np.mean((y_test[high_idx] - y_pred[high_idx]) ** 2))

            # Add to chart
            plt.figtext(0.5, -0.02,
                        f'{self.translate("Low Range RMSE")}={low_rmse:.4f}, {self.translate("Mid Range RMSE")}={mid_rmse:.4f}, {self.translate("High Range RMSE")}={high_rmse:.4f}',
                        ha='center', fontsize=8, transform=plt.gca().transAxes)

        # Add title and explanation
        plt.suptitle(self.translate('Model Prediction Quantile Analysis (Q-Q Plot)'), fontsize=16, fontweight='bold')

        plt.figtext(0.5, 0.01,
                    self.translate(
                        'Note: Q-Q plots compare the distribution shapes of predictions versus actual values.\n'
                        'Points along the diagonal line indicate matching distributions.\n'
                        'QQ-RMSE measures how closely the prediction distribution matches the actual data distribution.'),
                    ha='center', fontsize=10, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))

        # FIXED: Use subplots_adjust instead of tight_layout
        plt.subplots_adjust(bottom=0.15, top=0.9, left=0.1, right=0.9, wspace=0.3, hspace=0.4)

        # Save image
        qq_path = os.path.join(output_dir, 'qq_plot_analysis.png')
        plt.savefig(qq_path, dpi=300, bbox_inches='tight')
        plt.close()

        # =========== 4. Residual analysis ===========
        plt.figure(figsize=(15, 10))

        # Create residual plot for each model
        for i, (name, y_pred) in enumerate(predictions.items()):
            plt.subplot(2, 3, i + 1)

            # Calculate residuals
            residuals = y_test - y_pred

            # Plot residual scatter plot
            plt.scatter(y_pred, residuals, alpha=0.5, s=30)
            plt.axhline(y=0, color='r', linestyle='-', alpha=0.8)

            # Plot LOWESS smoothing line to show trend
            try:
                import statsmodels.api as sm
                lowess = sm.nonparametric.lowess
                z = lowess(residuals, y_pred, frac=0.3)
                plt.plot(z[:, 0], z[:, 1], 'b-', lw=2)
            except ImportError:
                # If statsmodels is not available, use simple moving average
                from scipy.ndimage import gaussian_filter1d

                # Sort for plotting smooth line
                sorted_indices = np.argsort(y_pred)
                sorted_preds = y_pred[sorted_indices]
                sorted_resids = residuals[sorted_indices]

                # Use Gaussian filter for smoothing
                smoothed = gaussian_filter1d(sorted_resids, sigma=10)
                plt.plot(sorted_preds, smoothed, 'b-', lw=2)

            plt.title(self.translate(f'{name} - Residual Analysis'), fontsize=12, fontweight='bold')
            plt.xlabel(self.translate('Predicted Value'), fontsize=10)
            plt.ylabel(self.translate('Residual (Actual - Predicted)'), fontsize=10)
            plt.grid(True, linestyle='--', alpha=0.7)

        # Add title and explanation
        plt.suptitle(self.translate('Model Prediction Residual Analysis'), fontsize=16, fontweight='bold')

        plt.figtext(0.5, 0.01,
                    self.translate(
                        'Note: Residual plots analyze model error patterns across different prediction values.\n'
                        'Ideally, residuals should be randomly distributed around the zero line.\n'
                        'Visible patterns (trends) indicate systematic model bias.'),
                    ha='center', fontsize=10, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))

        # FIXED: Use subplots_adjust instead of tight_layout
        plt.subplots_adjust(bottom=0.15, top=0.9, left=0.1, right=0.9, wspace=0.3, hspace=0.3)

        # Save image
        residual_path = os.path.join(output_dir, 'residual_analysis.png')
        plt.savefig(residual_path, dpi=300, bbox_inches='tight')
        plt.close()

    def print_summary(self, results):
        """
        Output experiment summary with clear insights
        Properly format the comparison table
        """
        # Clean results by removing prediction arrays
        cleaned_results = {}
        for model_name, metrics in results.items():
            cleaned_results[model_name] = {k: v for k, v in metrics.items() if k != 'y_pred'}

        df = pd.DataFrame(cleaned_results).T

        # Calculate normalized scores (0-1 scale, higher is better)
        df_scores = pd.DataFrame(index=df.index)

        # For metrics where lower is better, invert the scale
        for metric in ['rmse', 'mae', 'train_time', 'pred_time', 'memory_mb']:
            max_val = df[metric].max()
            min_val = df[metric].min()
            # Normalize and invert: 1 - (x - min) / (max - min)
            if max_val > min_val:  # Avoid division by zero
                df_scores[metric] = 1 - (df[metric] - min_val) / (max_val - min_val)
            else:
                df_scores[metric] = 1.0

        # For R² (higher is better), normalize directly
        max_r2 = df['r2'].max()
        min_r2 = df['r2'].min()
        if max_r2 > min_r2:  # Avoid division by zero
            df_scores['r2'] = (df['r2'] - min_r2) / (max_r2 - min_r2)
        else:
            df_scores['r2'] = 1.0

        # Create weights for different types of metrics
        weights = {
            'rmse': 0.25,  # Accuracy
            'mae': 0.15,  # Accuracy
            'r2': 0.20,  # Explanatory power
            'train_time': 0.15,  # Training efficiency
            'pred_time': 0.15,  # Inference efficiency
            'memory_mb': 0.10  # Resource efficiency
        }

        # Calculate weighted scores
        df_scores['total_score'] = sum(df_scores[m] * weights[m] for m in weights)

        # Find best models for each metric
        best_rmse = df['rmse'].idxmin()
        best_mae = df['mae'].idxmin()
        best_r2 = df['r2'].idxmax()
        fastest_train = df['train_time'].idxmin()
        fastest_pred = df['pred_time'].idxmin()
        lowest_memory = df['memory_mb'].idxmin()

        # Find overall best model
        best_overall = df_scores['total_score'].idxmax()

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('📊 Model Comparison Summary'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Print best model for each metric
        self.stdout.write('\n🥇 Best for each metric:')
        self.stdout.write(f'  • Prediction Accuracy (RMSE): {best_rmse} ({df.loc[best_rmse, "rmse"]:.4f})')
        self.stdout.write(f'  • Prediction Accuracy (MAE): {best_mae} ({df.loc[best_mae, "mae"]:.4f})')
        self.stdout.write(f'  • Explained Variance (R²): {best_r2} ({df.loc[best_r2, "r2"]:.4f})')
        self.stdout.write(f'  • Training Speed: {fastest_train} ({df.loc[fastest_train, "train_time"]:.2f} seconds)')
        self.stdout.write(f'  • Prediction Speed: {fastest_pred} ({df.loc[fastest_pred, "pred_time"]:.4f} seconds)')
        self.stdout.write(f'  • Memory Efficiency: {lowest_memory} ({df.loc[lowest_memory, "memory_mb"]:.2f}MB)')

        # Print overall best model
        self.stdout.write(self.style.SUCCESS(f'\n🏆 Best Overall Model: {best_overall}'))
        self.stdout.write(f'  • Balanced Score: {df_scores.loc[best_overall, "total_score"]:.4f} / 1.00')
        self.stdout.write(f'  • RMSE: {df.loc[best_overall, "rmse"]:.4f}')
        self.stdout.write(f'  • R²: {df.loc[best_overall, "r2"]:.4f}')
        self.stdout.write(f'  • Training Time: {df.loc[best_overall, "train_time"]:.2f} seconds')

        # Print comparison table - properly formatted
        self.stdout.write('\n📋 Complete Comparison Table:')

        # Add score to comparison table
        comparison_table = df.copy()
        comparison_table['score'] = df_scores['total_score']

        # Sort by score for better readability
        comparison_table = comparison_table.sort_values('score', ascending=False)

        # Format the table for better readability
        pd.set_option('display.precision', 4)  # Set precision for all float columns
        pd.set_option('display.width', 120)  # Wider display
        formatted_table = comparison_table.round({
            'rmse': 4, 'mae': 4, 'r2': 4,
            'train_time': 2, 'pred_time': 4, 'memory_mb': 2, 'score': 4
        })

        # Print the formatted table
        self.stdout.write(str(formatted_table))

        # Add recommendations
        self.stdout.write('\n💡 Recommendations:')

        # Recommend based on different scenarios
        if best_rmse == best_overall:
            self.stdout.write(f'  • Best Overall Performance and Prediction Accuracy: {best_overall}')
        else:
            self.stdout.write(f'  • Best Overall Performance: {best_overall}')
            self.stdout.write(f'  • Best Prediction Accuracy: {best_rmse}')

        if fastest_train == fastest_pred:
            self.stdout.write(f'  • Fastest Training and Prediction: {fastest_train}')
        else:
            self.stdout.write(f'  • Fastest Training: {fastest_train}')
            self.stdout.write(f'  • Fastest Prediction: {fastest_pred}')

        # Deployment recommendations
        self.stdout.write('\n🚀 Deployment Suggestions:')
        if df.loc[best_overall, 'memory_mb'] > df['memory_mb'].median():
            self.stdout.write(f'  • High-Performance Server Deployment: {best_overall} (higher memory requirements)')

            # Find a model that's good but uses less memory
            low_memory_models = df[df['memory_mb'] < df['memory_mb'].median()].index
            if len(low_memory_models) > 0:
                low_mem_scores = df_scores.loc[low_memory_models, 'total_score']
                best_low_mem = low_mem_scores.idxmax()
                self.stdout.write(f'  • Resource-Constrained Environment: {best_low_mem} (lower memory requirements)')
        else:
            self.stdout.write(f'  • General Deployment Recommendation: {best_overall} (balanced resource requirements)')

        # Recommend fastest model for real-time inference
        self.stdout.write(f'  • Real-Time Inference System: {fastest_pred} (lowest latency)')

        self.stdout.write(self.style.SUCCESS('=' * 80))

    def save_best_model(self, results, models, output_dir, feature_names):
        """Save the best performing model and feature_names"""
        # Choose best model based on balanced score
        # Clean results by removing prediction arrays
        cleaned_results = {}
        for model_name, metrics in results.items():
            cleaned_results[model_name] = {k: v for k, v in metrics.items() if k != 'y_pred'}

        df = pd.DataFrame(cleaned_results).T

        # Calculate normalized scores (0-1 scale, higher is better)
        df_scores = pd.DataFrame(index=df.index)

        # For metrics where lower is better, invert the scale
        for metric in ['rmse', 'mae', 'train_time', 'pred_time', 'memory_mb']:
            max_val = df[metric].max()
            min_val = df[metric].min()
            if max_val > min_val:
                df_scores[metric] = 1 - (df[metric] - min_val) / (max_val - min_val)
            else:
                df_scores[metric] = 1.0

        max_r2 = df['r2'].max()
        min_r2 = df['r2'].min()
        if max_r2 > min_r2:
            df_scores['r2'] = (df['r2'] - min_r2) / (max_r2 - min_r2)
        else:
            df_scores['r2'] = 1.0

        # Create weights for different types of metrics
        weights = {
            'rmse': 0.25,  # Accuracy
            'mae': 0.15,  # Accuracy
            'r2': 0.20,  # Explanatory power
            'train_time': 0.15,  # Training efficiency
            'pred_time': 0.15,  # Inference efficiency
            'memory_mb': 0.10  # Resource efficiency
        }

        # Calculate weighted scores
        df_scores['total_score'] = sum(df_scores[m] * weights[m] for m in weights)

        # Select best model based on balanced score
        best_model_name = df_scores['total_score'].idxmax()
        best_model = models[best_model_name]

        # Also record most accurate model
        best_rmse_name = df['rmse'].idxmin()
        best_rmse_model = models[best_rmse_name]

        self.stdout.write(
            f'💾 Saving best balanced model: {best_model_name} (Score: {df_scores.loc[best_model_name, "total_score"]:.4f})')
        if best_rmse_name != best_model_name:
            self.stdout.write(
                f'💾 Also saving most accurate model: {best_rmse_name} (RMSE: {df.loc[best_rmse_name, "rmse"]:.4f})')

        # Create model directory
        try:
            model_dir = os.path.join('recommendation', 'engine', 'models')
            os.makedirs(model_dir, exist_ok=True)

            # Extract and save best model parameters
            best_model_params = {}
            if hasattr(best_model, 'get_params'):
                best_model_params = best_model.get_params()
                # Filter out non-serializable parameters
                for key in list(best_model_params.keys()):
                    if callable(best_model_params[key]) or type(best_model_params[key]).__module__ == 'numpy':
                        best_model_params[key] = str(best_model_params[key])

            # Save parameters as JSON
            import json
            params_path = os.path.join(model_dir, 'best_model_params.json')
            with open(params_path, 'w') as f:
                json.dump(best_model_params, f, indent=2)

            self.stdout.write(self.style.SUCCESS(f'✅ Best model parameters saved: {params_path}'))

            # Save both models
            self._save_model(best_model, best_model_name, model_dir, feature_names, 'balanced')
            if best_rmse_name != best_model_name:
                self._save_model(best_rmse_model, best_rmse_name, model_dir, feature_names, 'accurate')

            # Save in standard format for compatibility
            if best_model_name == 'LightGBM' and LIGHTGBM_AVAILABLE:
                # For LightGBM, also save the best model in standard format
                joblib_path = os.path.join(model_dir, 'gbdt_model.joblib')
                joblib.dump(best_model, joblib_path, compress=3)
            elif best_model_name != 'NeuralNetwork':
                model_path = os.path.join(model_dir, 'gbdt_model.joblib')
                joblib.dump(best_model, model_path, compress=3)

            # Export performance report
            df.to_csv(os.path.join(output_dir, 'model_performance.csv'))

            # Export detailed model information
            with open(os.path.join(output_dir, 'model_info.txt'), 'w', encoding='utf-8') as f:
                f.write(f'Best Balanced Model: {best_model_name}\n')
                f.write(f'Score: {df_scores.loc[best_model_name, "total_score"]:.4f}\n')
                f.write(f'RMSE: {df.loc[best_model_name, "rmse"]:.4f}\n')
                f.write(f'MAE: {df.loc[best_model_name, "mae"]:.4f}\n')
                f.write(f'R²: {df.loc[best_model_name, "r2"]:.4f}\n')
                f.write(f'Training Time: {df.loc[best_model_name, "train_time"]:.2f} seconds\n')
                f.write(f'Prediction Time: {df.loc[best_model_name, "pred_time"]:.4f} seconds\n')
                f.write(f'Memory Usage: {df.loc[best_model_name, "memory_mb"]:.2f} MB\n\n')

                if best_rmse_name != best_model_name:
                    f.write(f'Most Accurate Model: {best_rmse_name}\n')
                    f.write(f'RMSE: {df.loc[best_rmse_name, "rmse"]:.4f}\n')
                    f.write(f'Score: {df_scores.loc[best_rmse_name, "total_score"]:.4f}\n\n')

                # Add scoring weights
                f.write('Scoring Weights:\n')
                for metric, weight in weights.items():
                    f.write(f'  {metric}: {weight}\n')

                # Add current date and time
                f.write(f'\nSaved on: {timezone.now()}\n')

            self.stdout.write(
                self.style.SUCCESS(f'✅ Model performance report saved: {os.path.join(output_dir, "model_info.txt")}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error saving model: {str(e)}'))
            traceback.print_exc()

    def _save_model(self, model, model_name, model_dir, feature_names, model_type):
        """Helper function to save a model"""
        try:
            if model_name == 'NeuralNetwork' and TENSORFLOW_AVAILABLE:
                # Fix: Add proper .keras extension for neural network models
                model_path = os.path.join(model_dir, f'{model_type}_nn_model.keras')
                model.save(model_path)
                self.stdout.write(self.style.SUCCESS(f'✅ Neural network model saved: {model_path}'))

            elif model_name == 'LightGBM' and LIGHTGBM_AVAILABLE:
                # Use native save method for LightGBM model
                model_path = os.path.join(model_dir, f'{model_type}_lgb_model.txt')
                if hasattr(model, 'save_model'):
                    model.save_model(model_path)
                    self.stdout.write(self.style.SUCCESS(f'✅ LightGBM model saved: {model_path}'))
                else:
                    # Fallback for scikit-learn wrapper
                    joblib_path = os.path.join(model_dir, f'{model_type}_model.joblib')
                    joblib.dump(model, joblib_path, compress=3)
                    self.stdout.write(self.style.SUCCESS(f'✅ Model saved: {joblib_path}'))

            else:
                # Save scikit-learn compatible model
                model_path = os.path.join(model_dir, f'{model_type}_model.joblib')
                joblib.dump(model, model_path, compress=3)
                self.stdout.write(self.style.SUCCESS(f'✅ Model saved: {model_path}'))

            # Save feature names
            if feature_names:
                with open(os.path.join(model_dir, f'{model_type}_feature_names.pkl'), 'wb') as f:
                    pickle.dump(feature_names, f)
                self.stdout.write(self.style.SUCCESS(
                    f'✅ Feature names saved: {os.path.join(model_dir, f"{model_type}_feature_names.pkl")}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to save model: {str(e)}'))
            traceback.print_exc()

    # Execute the script directly if run as standalone
    if __name__ == "__main__":
        try:
            from django.core.management import execute_from_command_line
            execute_from_command_line(sys.argv)
        except ImportError:
            # Allow standalone execution without Django
            cmd = Command()

            # Parse command line arguments manually if running standalone
            import argparse
            parser = argparse.ArgumentParser(description='Compare machine learning models for anime recommendation')
            cmd.add_arguments(parser)
            args = parser.parse_args()

            # Convert namespace to dictionary
            options = vars(args)

            # Execute the command
            cmd.handle(**options)