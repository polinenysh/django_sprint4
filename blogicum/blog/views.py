from django.shortcuts import get_object_or_404, redirect
from django.http import Http404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    DetailView, ListView, CreateView, UpdateView, DeleteView)
from django.core.paginator import Paginator
from django.urls import reverse, reverse_lazy
from django.db.models import Count
from .models import Post, Category, Comment
from .forms import PostForm, CommentForm, ProfileEditForm
from django.utils import timezone


def get_posts_queryset(for_user=None, category_slug=None, current_user=None):
    """
    Универсальная функция для получения постов.
    Args:
        for_user: Если указан - посты этого пользователя
        category_slug: Если указан - посты этой категории
        current_user: Текущий авторизованный пользователь (для проверки прав)
    Returns:
        QuerySet постов с учетом фильтров
    """
    if for_user:
        # Посты конкретного пользователя
        queryset = for_user.posts.all()

        # Если передан current_user и он не автор - фильтруем опубликованные
        if current_user and current_user != for_user:
            queryset = queryset.filter(
                pub_date__lte=timezone.now(),
                is_published=True
            )

    elif category_slug:
        # Посты категории
        category = get_object_or_404(
            Category, slug=category_slug, is_published=True)
        queryset = Post.objects.filter(
            category=category,
            is_published=True,
            pub_date__lte=timezone.now()
        )

    else:
        # Все опубликованные посты
        queryset = Post.objects.filter(
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True
        )

    return queryset.select_related('author', 'category', 'location')


def annotate_comments(queryset):
    """Функция для аннотации количества комментариев"""
    return queryset.annotate(comment_count=Count('comments')).order_by(
        '-pub_date')


class PostsListView(ListView):
    """
    Класс для вывода всех постов на главной странице.
    На каждой странице 10 постов начиная с последнего опубликованного.
    """

    model = Post
    template_name = 'blog/index.html'

    def get_queryset(self):
        queryset = get_posts_queryset()
        return annotate_comments(queryset)

    paginate_by = 10


class PostDetailView(DetailView):
    """Класс для детального просмотра поста и комментариев к нему"""

    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get_object(self, queryset=None):
        post_id = self.kwargs.get(self.pk_url_kwarg)
        post = get_object_or_404(Post, pk=post_id)
        user = self.request.user
        # Если пользователь - автор поста - возвращаем пост
        # Иначе проверяем может ли пользователь просматривать данный пост,
        # если нет - возвращаем 404
        if user == post.author:
            return post
        elif all([
            post.is_published,
            post.pub_date <= timezone.now(),
            post.category.is_published,
        ]):
            return post

        raise Http404

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comments.select_related('author')
        return context


class CategoryListView(ListView):
    """Просмотр всех публикаций в категории"""

    model = Category
    template_name = 'blog/category.html'
    paginate_by = 10

    def get_queryset(self):
        self.category = get_object_or_404(
            Category,
            slug=self.kwargs['category_slug'],
            is_published=True
        )
        queryset = get_posts_queryset(
            category_slug=self.kwargs['category_slug'])
        return annotate_comments(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class ProfileDetailView(DetailView):
    """Детальный просмотр профиля - посты, комментарии к ним"""

    model = get_user_model()
    template_name = 'blog/profile.html'
    context_object_name = 'profile'

    def get_object(self, queryset=None):
        """Получаем пользователя по username."""
        username = self.kwargs.get('username')
        return get_object_or_404(self.model, username=username)

    def get_context_data(self, **kwargs):
        """Добавляем посты пользователя с пагинацией."""
        context = super().get_context_data(**kwargs)
        user = self.object

        queryset = annotate_comments(get_posts_queryset(
            for_user=user, current_user=self.request.user))

        paginator = Paginator(queryset, 10)
        page_number = self.request.GET.get('page', 1)
        context['page_obj'] = paginator.get_page(page_number)

        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    """Создание публикации"""

    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        """Проверка валидности формы заполнения поста"""
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        """В случае успеха пересылаем на страницу профиля"""
        return reverse('blog:profile',
                       kwargs={'username': self.request.user.username})


class PostUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование поста"""

    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        """Проверяем, что текущий юзер - автор поста"""
        post = self.get_object()
        if request.user != post.author:
            messages.error(request,
                           'Вы можете редактировать только свои публикации.')
            return redirect('blog:post_detail', post_id=post.id)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """В случае успеха пересылаем на страницу профиля"""
        return reverse('blog:post_detail',
                       kwargs={'post_id': self.kwargs['post_id']})


class CommentCreateView(LoginRequiredMixin, CreateView):
    """Создание комментария"""

    model = Comment
    form_class = CommentForm
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        """Получаем объект поста или 404"""
        self.object_post = get_object_or_404(Post, pk=kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """
        Автоматически заполняем автора комментария
        и пост, к которому он относится
        """
        form.instance.author = self.request.user
        form.instance.post = self.object_post
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['post'] = self.post
        return context

    def get_success_url(self):
        """В случае успеха пересылаем на детальный просмотр поста"""
        return reverse('blog:post_detail',
                       kwargs={'post_id': self.kwargs['post_id']})


class CommentUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование комментария"""

    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        """Проверяем, что текущий юзер - автор комментария"""
        comment = self.get_object()
        if request.user != comment.author:
            messages.error(request,
                           'Вы можете редактировать только свои комментарии.')
            return redirect('blog:post_detail', post_id=comment.post.id)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """В случае успеха пересылаем на детальный просмотр поста"""
        return reverse('blog:post_detail',
                       kwargs={'post_id': self.kwargs['post_id']})


class PostDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление поста"""

    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'
    # В случае успешного удаления пересылаем на главную
    success_url = reverse_lazy('blog:index')

    def dispatch(self, request, *args, **kwargs):
        """Проверяем, что текущий юзер - автор поста"""
        post = self.get_object()
        if request.user != post.author:
            messages.error(request,
                           'Вы можете удалять только свои публикации.')
            return redirect('blog:post_detail', post_id=post.id)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PostForm(instance=self.object)
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Публикация успешно удалена.')
        return super().delete(request, *args, **kwargs)


class CommentDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление комментария"""

    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        """Проверяем, что текущий юзер - автор комментария"""
        comment = self.get_object()
        if request.user != comment.author:
            messages.error(request,
                           'Вы можете удалять только свои комментарии.')
            return redirect('blog:post_detail', post_id=comment.id)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """В случае успеха пересылаем на детальный просмотр поста"""
        messages.success(self.request, 'Комментарий удален')
        return reverse(
            'blog:post_detail', kwargs={'post_id': self.object.post.id})


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Обновление профиля"""

    model = get_user_model()
    form_class = ProfileEditForm
    template_name = 'blog/user.html'

    def get_object(self, queryset=None):
        """Получаем текущего пользователя"""
        return self.request.user

    def get_success_url(self):
        """В случае успеха пересылаем на страницу профиля"""
        return reverse('blog:profile',
                       kwargs={'username': self.object.username})
