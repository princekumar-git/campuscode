from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta

class User(AbstractUser):
    ROLE_CHOICES = [
        ('Student', 'Student'),
        ('Admin', 'Admin'),
    ]

    submissions: models.Manager['Submission']
    contests: models.Manager['Contest']
    
    role = models.CharField(max_length=20, default='Student', choices=ROLE_CHOICES) 
    college = models.CharField(max_length=100, default='CampusCode Institute')
    streak = models.IntegerField(default=0)
    college_rank = models.IntegerField(default=0)
    global_rank = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    xp = models.IntegerField(default=0)
    problem_solved = models.IntegerField(default=0)

    @property
    def xp_percentage(self):
        return min((self.xp / 2000) * 100, 100)
    
    @property
    def problems_solved(self):
        return self.submissions.filter(passed=True).values('problem').distinct().count()
    
    @property
    def last_solved_time(self):
        last_submission = self.submissions.filter(passed=True).order_by('-submitted_at').first()
        if last_submission:
            return last_submission.submitted_at.strftime('%B %d, %Y at %I:%M %p')
        return 'No problems solved yet'
    
    @property
    def recent_activities(self):
        """
        Fetch recent activities from all sources (submissions, forum, contests)
        Returns a sorted list of the last 20 activities across all types (from any time period)
        """
        from .models import ForumThread, ForumReply, Contest
        
        activities = []
        now = timezone.now()
        
        submissions = self.submissions.select_related('problem').order_by('-submitted_at')[:50]
        for submission in submissions:
            time_diff = now - submission.submitted_at
            time_ago = self._format_time_ago(time_diff)
            
            status = 'solved' if submission.passed else 'failed'
            description = f"Solved in {submission.language.capitalize()}" if submission.passed else "Failed Test Case"
            
            activities.append({
                'title': submission.problem.title,
                'description': description,
                'type': 'problem',
                'status': status,
                'time_ago': time_ago,
                'timestamp': submission.submitted_at,
                'icon': 'fa-code' if status == 'solved' else 'fa-times',
                'color': 'green' if status == 'solved' else 'red'
            })
        
        contests = self.contests.all().order_by('-id')[:50]
        for contest in contests:
            try:
                time_diff = now - contest.start_time
                time_ago = self._format_time_ago(time_diff)
                
                activities.append({
                    'title': contest.title,
                    'description': f"Registered for contest",
                    'type': 'contest',
                    'status': contest.status.lower(),
                    'time_ago': time_ago,
                    'timestamp': contest.start_time,
                    'icon': 'fa-trophy',
                    'color': 'blue'
                })
            except:
                pass
        
        forum_threads = ForumThread.objects.filter(author=self).select_related('category').order_by('-created_at')[:50]
        for thread in forum_threads:
            time_diff = now - thread.created_at
            time_ago = self._format_time_ago(time_diff)
            
            activities.append({
                'title': thread.title,
                'description': f"Started forum discussion in {thread.category.name if thread.category else 'General'}",
                'type': 'forum_thread',
                'status': 'active',
                'time_ago': time_ago,
                'timestamp': thread.created_at,
                'icon': 'fa-comments',
                'color': 'purple'
            })
        
        forum_replies = ForumReply.objects.filter(author=self).select_related('thread').order_by('-created_at')[:50]
        for reply in forum_replies:
            time_diff = now - reply.created_at
            time_ago = self._format_time_ago(time_diff)
            
            activities.append({
                'title': reply.thread.title,
                'description': f"Replied to forum discussion",
                'type': 'forum_reply',
                'status': 'active',
                'time_ago': time_ago,
                'timestamp': reply.created_at,
                'icon': 'fa-reply',
                'color': 'indigo'
            })
        
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:20]
    
    def _format_time_ago(self, time_diff):
        """Helper method to format time difference into readable format"""
        if time_diff < timedelta(minutes=1):
            return 'just now'
        elif time_diff < timedelta(hours=1):
            mins = time_diff.seconds // 60
            return f'{mins}m ago'
        elif time_diff < timedelta(days=1):
            hours = time_diff.seconds // 3600
            return f'{hours}h ago'
        elif time_diff < timedelta(days=7):
            days = time_diff.days
            return f'{days}d ago'
        elif time_diff < timedelta(days=30):
            weeks = time_diff.days // 7
            return f'{weeks}w ago'
        else:
            months = time_diff.days // 30
            return f'{months}mo ago'
    
    def __str__(self):
        return self.username

class Problem(models.Model):
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    
    title = models.CharField(max_length=200)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    points = models.IntegerField(default=10)
    acceptance = models.CharField(max_length=10, default='0%')
    tags = models.CharField(max_length=200, blank=True)
    
    statement = models.TextField()
    input_fmt = models.TextField(verbose_name="Input Format")
    output_fmt = models.TextField(verbose_name="Output Format")
    constraints = models.TextField()
    
    sample_input = models.TextField(blank=True, null=True)
    sample_output = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

class TestCase(models.Model):
    """
    Hidden test cases used for grading code submissions via Piston.
    """
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='test_cases')
    input_data = models.TextField(help_text="The stdin input given to the code")
    expected_output = models.TextField(help_text="The expected stdout output from the code")
    is_hidden = models.BooleanField(default=True, help_text="If True, the user won't see the input/output on failure")

    def __str__(self):
        return f"TestCase for {self.problem.title} (Hidden: {self.is_hidden})"

class Submission(models.Model):
    """
    Tracks every code submission attempt.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    code = models.TextField()
    language = models.CharField(max_length=50, default='python')
    passed = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "Passed" if self.passed else "Failed"
        return f"{self.user.username} - {self.problem.title} - {status}"

class Contest(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    rules = models.TextField(blank=True)
    prizes = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, default='Upcoming')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    participants = models.IntegerField(default=0)
    registered_users = models.ManyToManyField(User, related_name='contests', blank=True)

    @property
    def duration(self):
        diff = self.end_time - self.start_time
        hours = diff.seconds // 3600
        return f"{hours} Hours"
    
    def __str__(self):
        return self.title

# =========================
# Forum Models (Student Only)
# =========================

class ForumCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class ForumThread(models.Model):
    id: int
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(
        ForumCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='OPEN'
    )
    views = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ForumReply(models.Model):
    thread = models.ForeignKey(
        ForumThread,
        on_delete=models.CASCADE,
        related_name='replies'
    )
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reply by {self.author.username}"


class ForumVote(models.Model):
    reply = models.ForeignKey(
        ForumReply,
        on_delete=models.CASCADE,
        related_name='votes'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    value = models.IntegerField(choices=[(1, 'Upvote'), (-1, 'Downvote')])

    class Meta:
        unique_together = ('reply', 'user')
    
    def __str__(self):
        return f"{self.user.username} voted {self.value}"