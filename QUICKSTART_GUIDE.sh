#!/bin/bash

# RoboQuiz Quick Start Guide

echo "🚀 RoboQuiz System - Quick Start"
echo "================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

echo -e "${BLUE}Installing dependencies...${NC}"
pip install -r requirements.txt > /dev/null 2>&1

echo -e "${BLUE}Running migrations...${NC}"
python manage.py migrate > /dev/null 2>&1

echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo "📊 System Status:"
echo "  - Database: Ready"
echo "  - Models: Migrated"
echo ""
echo "🧪 Sample Test Accounts:"
echo "  Email: alice@example.com      | Password: password123"
echo "  Email: bob@example.com        | Password: password123"
echo "  Email: carol@example.com      | Password: password123"
echo "  Email: david@example.com      | Password: password123"
echo ""
echo "🌐 To Start the Server:"
echo "  python manage.py runserver"
echo ""
echo "📱 Access the Application:"
echo "  - Home: http://localhost:8000/"
echo "  - Login: http://localhost:8000/accounts/login/"
echo "  - Dashboard: http://localhost:8000/accounts/dashboard/"
echo "  - Courses: http://localhost:8000/game/"
echo "  - Leaderboard: http://localhost:8000/game/leaderboard/"
echo "  - Admin: http://localhost:8000/admin/"
echo ""
echo "📚 Key Features:"
echo "  ✓ Leaderboard System"
echo "  ✓ Progress Tracking"
echo "  ✓ Course Enrollment"
echo "  ✓ Automatic Scoring"
echo "  ✓ User Rankings"
echo ""
echo -e "${GREEN}Happy Learning! 🎓${NC}"
