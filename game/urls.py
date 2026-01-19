from django.urls import path
from . import views

app_name = "game"

urlpatterns = [
    # Home and listings
    path('', views.game_home, name='home'),
    
    # Chapters (teaching materials)
    path('chapter/<int:chapter_id>/', views.chapter_detail, name='chapter_detail'),
    path('enroll/<int:chapter_id>/', views.enroll_chapter, name='enroll'),
    
    # Challenges (quizzes and coding)
    path('challenge/<int:challenge_id>/', views.challenge_detail, name='challenge_detail'),
    
    # Quiz questions
    path('quiz/<int:question_id>/', views.quiz_view, name='quiz'),
    path('check/<int:question_id>/', views.check_answer, name='check'),
    
    # Leaderboard
    path('leaderboard/', views.leaderboard, name='leaderboard'),
]
