# Team Charter — Crypto Volatility Detection

## Project
Real-Time Crypto AI Service — Team Project

## Team Members & Roles

| Member | Role | Responsibilities |
|--------|------|-----------------|
| Eshita Rajvegesna | ML Lead / Base Model Owner | Individual pipeline, XGBoost model, feature engineering, MLflow tracking |
| [Member 2] | Infrastructure Lead | Docker orchestration, Kafka setup, deployment |
| [Member 3] | API Lead | FastAPI endpoints, monitoring, integration |
| [Member 4] | Data Lead | Data collection, EDA, drift monitoring |
| [Member 5] | DevOps Lead | CI/CD, GitHub Actions, load testing |

## Model Selection
We are using Eshita's individual XGBoost model as the team base model.
See docs/selection_rationale.md for full justification.

## Ways of Working
- Weekly sync meetings to align on progress
- All code reviewed before merging
- MLflow used for all experiment tracking
- Evidently reports generated weekly for drift monitoring
- GitHub Actions for CI/CD

## Communication
- Primary: Slack / Discord
- Code: GitHub repository
- Docs: Shared Google Drive

## Definition of Done
- All endpoints tested with curl
- MLflow shows experiment runs
- Evidently drift report generated
- Docker Compose brings up all services with one command
- PR-AUC reported and meets 0.55 target
