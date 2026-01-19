from django.contrib.auth.models import User
from django.utils import timezone
from game.models import Chapter, Question, Option, CourseEnrollment, QuestionAttempt, UserScore

# Clear existing data
print("Clearing existing data...")
Question.objects.all().delete()
Chapter.objects.all().delete()
QuestionAttempt.objects.all().delete()
UserScore.objects.all().delete()
CourseEnrollment.objects.all().delete()

# Create Chapters
print("Creating chapters...")
chapter1 = Chapter.objects.create(
    title="Introduction to C++",
    description="Learn the basics of C++ programming including variables, data types, and operators.",
    order=1
)

chapter2 = Chapter.objects.create(
    title="Control Flow",
    description="Master if statements, loops, and decision-making in C++ programs.",
    order=2
)

chapter3 = Chapter.objects.create(
    title="Functions and Pointers",
    description="Understand how to write reusable functions and work with memory pointers.",
    order=3
)

# Create Questions for Chapter 1
print("Creating questions for Chapter 1...")
questions_ch1 = [
    {
        "story": "Robo-X needs to declare an integer variable called 'score'. What's the correct syntax?",
        "code": "int score 100;",
        "hint": "Variables need an equals sign for initialization, not a space.",
        "points": 100,
        "correct_option": "int score = 100;",
    },
    {
        "story": "Fix the bug in this code that should add two numbers together.",
        "code": "int sum = 5 + 10\nstd::cout << sum;",
        "hint": "Check if all statements end with a semicolon.",
        "points": 100,
        "correct_option": "int sum = 5 + 10;\nstd::cout << sum;",
    },
    {
        "story": "Which data type should you use for storing a person's age?",
        "code": "float age = 25;",
        "hint": "Age is a whole number, not a decimal.",
        "points": 100,
        "correct_option": "int age = 25;",
    },
]

for i, q_data in enumerate(questions_ch1):
    q = Question.objects.create(
        chapter=chapter1,
        story=q_data["story"],
        code=q_data["code"],
        hint=q_data["hint"],
        points=q_data["points"],
        order=i + 1
    )
    
    # Create options
    Option.objects.create(
        question=q,
        text=q_data["correct_option"],
        is_correct=True
    )
    
    # Add wrong options
    wrong_options = [
        "int score 100;",
        "score = 100;",
        "var score = 100;",
    ]
    
    for wrong in wrong_options[:2]:
        if wrong != q_data["correct_option"]:
            Option.objects.create(
                question=q,
                text=wrong,
                is_correct=False
            )

# Create Questions for Chapter 2
print("Creating questions for Chapter 2...")
questions_ch2 = [
    {
        "story": "What does this if statement check?",
        "code": "if (x > 5) { std::cout << \"Greater\"; }",
        "hint": "The > operator means 'greater than'.",
        "points": 100,
        "correct_option": "Checks if x is greater than 5",
    },
    {
        "story": "Which loop will execute exactly 5 times?",
        "code": "for (int i = 0; i < 5; i++)",
        "hint": "The loop continues while i < 5.",
        "points": 100,
        "correct_option": "for (int i = 0; i < 5; i++)",
    },
]

for i, q_data in enumerate(questions_ch2):
    q = Question.objects.create(
        chapter=chapter2,
        story=q_data["story"],
        code=q_data["code"],
        hint=q_data["hint"],
        points=q_data["points"],
        order=i + 1
    )
    
    # Create options
    Option.objects.create(
        question=q,
        text=q_data["correct_option"],
        is_correct=True
    )
    
    Option.objects.create(
        question=q,
        text="Incorrect option 1",
        is_correct=False
    )

# Create Questions for Chapter 3
print("Creating questions for Chapter 3...")
questions_ch3 = [
    {
        "story": "What does a pointer store?",
        "code": "int* ptr = &variable;",
        "hint": "The & operator gets the address of a variable.",
        "points": 100,
        "correct_option": "The memory address of a variable",
    },
]

for i, q_data in enumerate(questions_ch3):
    q = Question.objects.create(
        chapter=chapter3,
        story=q_data["story"],
        code=q_data["code"],
        hint=q_data["hint"],
        points=q_data["points"],
        order=i + 1
    )
    
    Option.objects.create(
        question=q,
        text=q_data["correct_option"],
        is_correct=True
    )
    
    Option.objects.create(
        question=q,
        text="The value of a variable",
        is_correct=False
    )

# Create sample users and their progress
print("Creating sample users with progress...")
users_data = [
    {"username": "alice@example.com", "first_name": "Alice", "last_name": "Johnson", "password": "password123"},
    {"username": "bob@example.com", "first_name": "Bob", "last_name": "Smith", "password": "password123"},
    {"username": "carol@example.com", "first_name": "Carol", "last_name": "Davis", "password": "password123"},
    {"username": "david@example.com", "first_name": "David", "last_name": "Wilson", "password": "password123"},
]

for user_data in users_data:
    user, created = User.objects.get_or_create(
        username=user_data["username"],
        defaults={
            "first_name": user_data["first_name"],
            "last_name": user_data["last_name"],
            "email": user_data["username"],
        }
    )
    if created:
        user.set_password(user_data["password"])
        user.save()
    
    # Create user score
    UserScore.objects.get_or_create(user=user)
    
    # Enroll in all chapters
    for chapter in [chapter1, chapter2, chapter3]:
        CourseEnrollment.objects.get_or_create(user=user, chapter=chapter)

# Simulate completion for demo purposes
print("Simulating user progress...")

# Alice - completed all of chapter 1 and 2, some of chapter 3
alice = User.objects.get(username="alice@example.com")
all_questions = Question.objects.all()

for question in all_questions[:5]:  # Complete first 5 questions
    correct_option = Option.objects.filter(question=question, is_correct=True).first()
    
    attempt = QuestionAttempt.objects.create(
        user=alice,
        question=question,
        selected_option=correct_option,
        is_correct=True,
        points_earned=question.points
    )
    attempt.attempted_at = timezone.now()
    attempt.save()

alice_score = UserScore.objects.get(user=alice)
alice_score.update_score()

# Bob - completed chapter 1
bob = User.objects.get(username="bob@example.com")
for question in all_questions[:3]:
    correct_option = Option.objects.filter(question=question, is_correct=True).first()
    attempt = QuestionAttempt.objects.create(
        user=bob,
        question=question,
        selected_option=correct_option,
        is_correct=True,
        points_earned=question.points
    )
    attempt.attempted_at = timezone.now()
    attempt.save()

bob_score = UserScore.objects.get(user=bob)
bob_score.update_score()

# Carol - completed 2 questions
carol = User.objects.get(username="carol@example.com")
for question in all_questions[:2]:
    correct_option = Option.objects.filter(question=question, is_correct=True).first()
    attempt = QuestionAttempt.objects.create(
        user=carol,
        question=question,
        selected_option=correct_option,
        is_correct=True,
        points_earned=question.points
    )
    attempt.attempted_at = timezone.now()
    attempt.save()

carol_score = UserScore.objects.get(user=carol)
carol_score.update_score()

print("\n✅ Sample data created successfully!")
print("\nTest users created:")
for user_data in users_data:
    print(f"  Email: {user_data['username']}, Password: {user_data['password']}")
