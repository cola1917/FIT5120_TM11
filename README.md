# NutriHeroes

NutriHeroes is a child-friendly mobile nutrition application designed to help children aged 7-12 build healthier eating habits through food scanning, personalised recommendations, educational stories, and small daily challenges. The app turns nutrition guidance into a playful superhero-themed experience so children can learn what foods support goals such as stronger muscles, better focus, good mood, clear vision, and overall wellbeing.

The project includes an Expo React Native mobile app and a FastAPI backend. The mobile app provides the user interface, profile management, camera-based food scanning flow, goal-based food recommendations, stories, and mini-games. The backend supports food image analysis, nutrition assessment, healthier alternative suggestions, daily challenge data, and integration with a PostgreSQL food catalogue.

## Key Features

- **Food scanning**: Children can scan a food item using the device camera and receive a child-friendly health assessment.
- **Healthier alternatives**: The app suggests healthier food swaps when a scanned food is less suitable.
- **Personalised profile**: Users can create a profile with age, avatar, food likes/dislikes, and foods they cannot eat.
- **Goal-based recommendations**: Food suggestions are organised around child-friendly health goals such as strength, growth, vision, focus, immunity, and mood.
- **Stories and food facts**: Educational story screens and food facts help explain healthy eating in a simple way.
- **Hero World activities**: Includes daily healthy challenges and the Meal Maker mini-game to encourage repeated engagement.
- **Backend nutrition support**: The FastAPI service provides scan analysis, daily challenges, caching, and food catalogue data.

## Tech Stack

### Mobile App

- Expo
- React Native
- TypeScript
- Expo Router
- AsyncStorage
- Expo Camera

### Backend

- FastAPI
- PostgreSQL
- SQLAlchemy
- OpenAI+Qwen integration
- Uvicorn

## Project Structure

```text
.
|-- app/                    # Expo Router screens and app navigation
|-- components/             # Reusable UI components and feature components
|-- services/               # Frontend API, profile, game, story, and challenge services
|-- assets/                 # Images, fonts, and other static assets
|-- nutri-health-api/       # FastAPI backend service
|-- tests/                  # Test documentation and reports
|-- DATA_DICTIONARY.md      # Database and data model documentation
`-- README.md               # Project overview and setup guide
```

## Getting Started

### Prerequisites

- Node.js and npm
- Expo CLI or `npx expo`
- Python 3.11+ for the backend
- PostgreSQL for backend data storage
- OpenAI+Qwen keys for image analysis

### Run the Mobile App

1. Install dependencies:
   
   ```bash
   npm install
   ```

2. Start the Expo development server:
   
   ```bash
   npx expo start
   ```

3. Open the app using one of the Expo options:
   
   - Android emulator
   - iOS simulator
   - Expo Go
   - Web preview

### Run the Backend API

1. Go to the backend folder:
   
   ```bash
   cd nutri-health-api
   ```

2. Create and activate a virtual environment:
   
   ```bash
   python -m venv venv
   ```
   
   On Windows:
   
   ```bash
   venv\Scripts\activate
   ```
   
   On macOS/Linux:
   
   ```bash
   source venv/bin/activate
   ```

3. Install backend dependencies:
   
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.example` and configure:
   
   ```text
   DATABASE_URL=your_postgresql_connection_string
   GEMINI_API_KEY=your_gemini_api_key
   ```

5. Start the API server:
   
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. Open the API documentation:
   
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

## Useful Commands

```bash
npm run start      # Start the Expo app
npm run android    # Run on Android
npm run ios        # Run on iOS
npm run web        # Run web preview
npm run lint       # Run Expo linting
```

## Documentation

- [Backend README](nutri-health-api/README.md)
- [Data Dictionary](DATA_DICTIONARY.md)
- [Seed Workflow](nutri-health-api/data/README-seed-workflow.md)
- [Pair Programming Document](PAIR_PROGRAMMING.md)

## Project Purpose

NutriHeroes aims to make nutrition education more approachable for children by combining practical food analysis with playful learning. Instead of presenting nutrition as complex medical information, the app uses simple language, visual feedback, goals, rewards, and interactive activities to help children understand food choices and develop healthier habits over time.
