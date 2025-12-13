from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.PostsListView.as_view(), name='index'),  # Главная
    path('posts/<int:post_id>/', views.PostDetailView.as_view(),
         name='post_detail'),   # Детальный просмотр поста
    path('posts/create/', views.PostCreateView.as_view(),
         name='create_post'),  # Создание поста
    path('posts/<int:post_id>/edit/', views.PostUpdateView.as_view(),
         name='edit_post'),  # Редактирование поста
    path('posts/<int:post_id>/comment/', views.CommentCreateView.as_view(),
         name='add_comment'),  # Добавление комментария
    path('posts/<int:post_id>/edit_comment/<int:comment_id>/',
         views.CommentUpdateView.as_view(),
         name='edit_comment'),  # Редактирование коммментария
    path('posts/<int:post_id>/delete/', views.PostDeleteView.as_view(),
         name='delete_post'),  # Удаление поста
    path('posts/<int:post_id>/delete_comment/<int:comment_id>/',
         views.CommentDeleteView.as_view(),
         name='delete_comment'),  # Удаление комментария
    path('category/<slug:category_slug>/', views.CategoryListView.as_view(),
         name='category_posts'),  # Страница категории
    path('profile/edit/', views.ProfileUpdateView.as_view(),
         name='edit_profile'),  # Редактирование профиля
    path('profile/<str:username>/', views.ProfileDetailView.as_view(),
         name='profile'),  # Просмотр профиля
]
