from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password
import re


def validate_course_duration(value):
    pattern = r'^(?P<value>([1-9]|[1-2][0-9]|30)) (?P<unit>(week|day|weeks|days))$'
    if not re.match(pattern, value):
        raise ValidationError("Enter a valid duration (e.g., '3 weeks' or '1 day').")


def validate_module_duration(value):
    pattern = r'^(?P<value>([1-9]|[1-2][0-9]|30)) (?P<unit>(hour|minute|hours|minutes))$'
    if not re.match(pattern, value):
        raise ValidationError("Enter a valid duration (e.g., '2 hours' or '15 minutes').")


class Student(models.Model):
    ROLE_CHOICES = [
        ("guest", "Guest"),
        ("student", "Student"),
        ("author", "Author"),
    ]

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="guest")
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    about = models.TextField(max_length=500, null=True, blank=True, default="")
    birthday = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    gender_choices = [("M", "Male"), ("F", "Female"), ("O", "Other")]
    gender = models.CharField(choices=gender_choices, null=True, max_length=1, blank=True)
    enrolled_courses = models.ManyToManyField("Course", blank=True, related_name="students")

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def is_enrolled(self, course):
        return self.enrolled_courses.filter(id=course.id).exists()

    def __str__(self):
        return f"{self.username} ({self.role})"



class Author(models.Model):
    user = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="author")

    def __str__(self):
        return f"Author: {self.user.username}"


class Course(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True, blank=True, related_name="authored_courses")
    LEVEL_CHOICES = [
        ("all", "All Levels"),
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("expert", "Expert"),
    ]
    description = models.TextField()
    duration = models.CharField(max_length=20, validators=[validate_course_duration])
    level = models.CharField(max_length=50, choices=LEVEL_CHOICES, default="all")
    course_image = models.ImageField(upload_to="course_images/", null=True, blank=True)

    def clean(self):
        pattern = r'^(?P<value>([1-9]|[1-2][0-9]|30)) (?P<unit>(week|day|weeks|days))$'
        if not re.match(pattern, self.duration):
            raise ValidationError("Enter a valid duration (e.g., '3 weeks' or '1 day').")

    def __str__(self):
        return self.title


class AuthorCourse(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date_published = models.DateField(auto_now_add=True)
    priority = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("author", "course")

    def __str__(self):
        return f"{self.author.user.username} - {self.course.title}"


class Module(models.Model):
    module = models.CharField(max_length=200)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    duration = models.CharField(max_length=20, validators=[validate_module_duration])

    def clean(self):
        pattern = r'^(?P<value>([1-9]|[1-2][0-9]|30)) (?P<unit>(hour|minute|hours|minutes))$'
        if not re.match(pattern, self.duration):
            raise ValidationError("Enter a valid duration (e.g., '2 hours' or '15 minutes').")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.module} - {self.course.title}"


class Lesson(models.Model):
    name = models.CharField(max_length=200)
    short_description = models.TextField(null=True, blank=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    video_url = models.URLField(blank=True, null=True)
    uploaded_video = models.FileField(upload_to="lesson_videos/", blank=True, null=True)
    content = models.TextField(null=True, blank=True)

    def clean(self):
        if self.video_url and self.uploaded_video:
            raise ValidationError("You cannot provide both a video URL and an uploaded video.")
        if not self.video_url and not self.uploaded_video:
            raise ValidationError("You must provide either a video URL or an uploaded video.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        self.module.course.update_total_lessons()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.module.course.update_total_lessons()

    def __str__(self):
        return f"{self.name} - {self.module.module}"


class Review(models.Model):
    user = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="reviews")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    feedback = models.TextField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "course")

    def clean(self):
        if not self.user.is_enrolled(self.course):
            raise ValidationError("You must be enrolled in this course to leave a review.")

    def __str__(self):
        return f"{self.user.username} - {self.course.title} ({self.rating}/5) ⭐"
