import io
import json
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count , Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from django.utils import timezone
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from .models import Submission, Contest
import re

# Make sure to import TestCase and Submission explicitly
 
from .models import (
    User,
    Problem,
    Contest,
    TestCase,
    Submission,
    ForumCategory,
    ForumThread,
    ForumReply,
    ForumVote,
)


PISTON_API = "https://emkc.org/api/v2/piston/execute"


def compute_and_update_ranks():
    """Recalculate and persist global and college ranks for all Students.

    Ranking rules:
    - Higher XP -> better (lower) rank (1 is best).
    - Users with equal XP receive the same rank (dense ranking).
    """
    students = User.objects.filter(role='Student').order_by('-xp', 'username')

    to_update = []

    # Global ranks (dense ranking)
    prev_xp = None
    rank = 0
    for u in students:
        if u.xp != prev_xp:
            rank += 1
            prev_xp = u.xp
        if u.global_rank != rank:
            u.global_rank = rank
            to_update.append(u)

    # College ranks (per college)
    colleges = students.values_list('college', flat=True).distinct()
    for college in colleges:
        col_students = students.filter(college=college)
        prev_xp = None
        rank = 0
        for u in col_students:
            if u.xp != prev_xp:
                rank += 1
                prev_xp = u.xp
            if u.college_rank != rank:
                u.college_rank = rank
                if u not in to_update:
                    to_update.append(u)

    if to_update:
        User.objects.bulk_update(to_update, ['global_rank', 'college_rank'])

# =========================================
# Authentication Views 
# =========================================

def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'index.html')

def signup_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        if not name or not email or not password:
            messages.error(request, 'All fields are required.')
            return redirect('index')
        
        if not re.match(r'^[a-zA-Z\s]+$', name):
            messages.error(request, 'Name should only contain letters.')
            return redirect('index')
        
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, email):
            messages.error(request, 'Please enter a valid email address.')
            return redirect('index')
        
        if len(password) < 6:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('index')
        
        if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
            messages.error(request, 'Password must contain both letters and numbers.')
            return redirect('index')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('index')

        user = User.objects.create_user(username=email, email=email, password=password)
        user.first_name = name 
        user.role = 'Student'
        user.streak = 1
        highest_rank = User.objects.filter(role='Student').order_by('global_rank').first()
        user.global_rank = highest_rank.global_rank + 1 if highest_rank else 1
        user.college_rank = highest_rank.college_rank + 1 if highest_rank else 1
        user.xp = 0
        user.save()

        login(request, user)
        return redirect('dashboard')
    
    return redirect('index')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)
            
            if user is not None:
                login(request, user)
                if getattr(user, 'role', 'Student') == 'Admin':
                    return redirect('admin_dashboard')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid password.')
        
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email.')
            
    return redirect('index')

def logout_view(request):
    logout(request)
    return redirect('index')

# =========================================
# Main Platform Views
# =========================================

@login_required
def dashboard(request):
    # Ensure ranks reflect current XP before rendering dashboard
    compute_and_update_ranks()
    
    # Get activity data for the last 7 days
    from datetime import datetime, timedelta
    today = timezone.now().date()
    week_start = today - timedelta(days=6)
    
    # Days of the week
    days_of_week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    activity_data = []
    
    # Get submissions for last 7 days, grouped by day
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        count = request.user.submissions.filter(
            submitted_at__date=day_date,
            passed=True
        ).count()
        activity_data.append(count)
    
    context = {
        'user': request.user,
        'activity_data': activity_data,
        'activity_labels': days_of_week
    }
    return render(request, 'dashboard.html', context)

@login_required
def problems(request):
    problems = Problem.objects.all()
    
    # Get solved problems for current user
    solved_submissions = Submission.objects.filter(user=request.user, passed=True).values_list('problem_id', flat=True)
    solved_ids = list(solved_submissions)
    
    return render(request, 'problems.html', {
        'problems': problems,
        'solved_ids': solved_ids
    })

@login_required
def solve_problem(request, id):
    problem = get_object_or_404(Problem, id=id)
    return render(request, 'problem_page.html', {'problem': problem})

@login_required
def contests(request):
    contests = Contest.objects.order_by('start_time')
    return render(request, 'contest.html', {'contests': contests})

@login_required
def contest_overview(request, id):
    contest = get_object_or_404(Contest, id=id)
    return render(request, 'contest_overview.html', {'contest': contest})

@login_required
def register_contest(request, id):
    """Handle contest registration"""
    if request.method == 'POST':
        contest = get_object_or_404(Contest, id=id)
        user = request.user
        
        # Check if user is already registered
        if contest.registered_users.filter(id=user.id).exists():
            return JsonResponse({
                'status': 'info',
                'message': 'You are already registered for this contest.'
            })
        
        # Check if contest status is not 'Ended'
        if contest.status == 'Ended':
            return JsonResponse({
                'status': 'error',
                'message': 'This contest has already ended. Registration is closed.'
            })
        
        # Register user
        contest.registered_users.add(user)
        contest.participants += 1
        contest.save()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Successfully registered for {contest.title}!',
            'participants': contest.participants
        })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method.'
    }, status=400)

@login_required
def forum(request):
    threads = ForumThread.objects.select_related('author', 'category') \
        .annotate(reply_count=Count('replies')) \
        .order_by('-created_at')

    categories = ForumCategory.objects.all()
    
    # Calculate total threads and replies
    total_threads = ForumThread.objects.count()
    total_replies = ForumReply.objects.count()
    
    # Get top contributors based on thread + reply count
    from django.db.models import Q
    top_contributors = User.objects.annotate(
        contribution_count=Count('forumthread') + Count('forumreply')
    ).filter(contribution_count__gt=0).order_by('-contribution_count')[:5]

    return render(request, 'forum.html', {
        'threads': threads,
        'categories': categories,
        'total_threads': total_threads,
        'total_replies': total_replies,
        'top_contributors': top_contributors,
    })

@login_required
def add_reply(request, thread_id):
    thread = get_object_or_404(ForumThread, id=thread_id)

    if request.method == 'POST':
        ForumReply.objects.create(
            thread=thread,
            content=request.POST.get('content'),
            author=request.user
        )

        # XP reward
        request.user.xp += 5
        request.user.save()

        # Update ranks since XP changed
        compute_and_update_ranks()

    return redirect('forum_thread_detail', thread_id=thread.id)

@login_required
def upvote_reply(request, reply_id):
    reply = get_object_or_404(ForumReply, id=reply_id)

    vote, created = ForumVote.objects.get_or_create(
        reply=reply,
        user=request.user,
        defaults={'value': 1}
    )

    if not created:
        vote.delete()  # toggle off
    else:
        reply.author.xp += 2
        reply.author.save()

        # Update ranks since XP changed
        compute_and_update_ranks()

    return redirect('forum_thread_detail', thread_id=reply.thread.id)

@login_required
def download_report_pdf(request):
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    
    user = request.user
    
    # --- GATHER DATA ---
    total_submissions = user.submissions.count()
    total_solved = user.submissions.filter(passed=True).count()
    accuracy = (total_solved / total_submissions * 100) if total_submissions > 0 else 0
    
    # Difficulty Stats
    easy_solved = user.submissions.filter(passed=True, problem__difficulty='Easy').count()
    easy_attempted = user.submissions.filter(problem__difficulty='Easy').count()
    easy_accuracy = (easy_solved / easy_attempted * 100) if easy_attempted > 0 else 0
    
    medium_solved = user.submissions.filter(passed=True, problem__difficulty='Medium').count()
    medium_attempted = user.submissions.filter(problem__difficulty='Medium').count()
    medium_accuracy = (medium_solved / medium_attempted * 100) if medium_attempted > 0 else 0
    
    hard_solved = user.submissions.filter(passed=True, problem__difficulty='Hard').count()
    hard_attempted = user.submissions.filter(problem__difficulty='Hard').count()
    hard_accuracy = (hard_solved / hard_attempted * 100) if hard_attempted > 0 else 0
    
    # Topic Proficiency - Get problems by tags
    topic_stats = {}
    for submission in user.submissions.filter(passed=True).select_related('problem'):
        if submission.problem.tags:
            for tag in submission.problem.tags.split(','):
                tag = tag.strip()
                if tag:
                    if tag not in topic_stats:
                        topic_stats[tag] = {'solved': 0, 'proficiency': 'Beginner'}
                    topic_stats[tag]['solved'] += 1
                    if topic_stats[tag]['solved'] >= 10:
                        topic_stats[tag]['proficiency'] = 'Expert'
                    elif topic_stats[tag]['solved'] >= 5:
                        topic_stats[tag]['proficiency'] = 'Advanced'
                    elif topic_stats[tag]['solved'] >= 2:
                        topic_stats[tag]['proficiency'] = 'Intermediate'
    
    # Contest History
    contest_history = []
    for contest in user.contests.all().order_by('-start_time')[:10]:
        # Calculate rank and percentile (mock data for now)
        contest_history.append({
            'name': contest.title,
            'date': contest.start_time.strftime('%b %d'),
            'solved': '3/6' if contest.status != 'Ended' else '4/5',
            'rank': '300',
            'percentile': '92.5%' if contest.status != 'Ended' else '78.0%'
        })
    
    # --- CREATE PDF ---
    buffer = io.BytesIO()
    
    # Setup PDF
    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=50,
        bottomMargin=30
    )
    
    styles = getSampleStyleSheet()
    story = []
    
    # Colors
    PRIMARY_COLOR = HexColor("#1E4A7A")
    SECONDARY_COLOR = HexColor("#3B82F6")
    TEXT_GREY = HexColor("#6B7280")
    LIGHT_GREY = HexColor("#F3F4F6")
    
    # --- HEADER ---
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading1'],
        fontSize=12,
        textColor=colors.black,
        fontName='Helvetica-Bold',
        spaceAfter=6
    )
    
    subheader_style = ParagraphStyle(
        'SubHeader',
        parent=styles['Normal'],
        fontSize=20,
        textColor=TEXT_GREY,
        fontName='Helvetica'
    )

    # Section title style (smaller than main header, left aligned)
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=colors.black,
        alignment=TA_LEFT,
        spaceBefore=6,
        spaceAfter=4
    )
    
    # Header Content: use local time for consistent timezone and clear ID format
    report_dt = timezone.localtime(timezone.now())
    report_date = report_dt.strftime('%m/%d/%Y')
    report_id = f"RPT-{report_dt.strftime('%Y%m')}-{user.id:03d}"

    header_data = [[
        'CC',
        Paragraph('<b>STUDENT CODING REPORT</b>', ParagraphStyle('htitle', parent=styles['Heading2'], alignment=TA_LEFT, fontSize=14)),
        Paragraph(f"Date: {report_date}<br/>ID: {report_id}", ParagraphStyle('meta', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT))
    ]]

    header_table = Table(header_data, colWidths=[0.9*inch, 3.0*inch, 1.8*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (0, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, 0), 14),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
    ]))

    story.append(header_table)
    story.append(Spacer(1, 0.15*inch))
    
    # --- SECTION 1: STUDENT PROFILE ---
    profile_title = Paragraph("STUDENT PROFILE", section_title_style)
    story.append(profile_title)
    
    profile_data = [
        ['NAME', f"{user.first_name} {user.last_name}" if user.first_name else user.username,
         'ROLL NO', f"{user.username}"],
        ['COLLEGE', user.college if user.college else "N/A",
         'REPORT PERIOD', 'Last 6 Months']
    ]
    
    profile_table = Table(profile_data, colWidths=[1*inch, 2*inch, 1.2*inch, 1.8*inch])
    profile_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), TEXT_GREY),
        ('FONT', (1, 0), (1, -1), 'Helvetica', 10),
        ('FONT', (3, 0), (3, -1), 'Helvetica', 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    story.append(profile_table)
    story.append(Spacer(1, 0.2*inch))
    
    # --- SECTION 2: PERFORMANCE SUMMARY ---
    perf_title = Paragraph("PERFORMANCE SUMMARY", section_title_style)
    story.append(perf_title)
    
    perf_data = [
        ['PROBLEMS SOLVED', str(total_solved), 'GLOBAL RANK', f"#{user.global_rank}"],
        ['ACCURACY', f"{accuracy:.1f}%", 'SKILL SCORE', str(user.xp)]
    ]
    
    perf_table = Table(perf_data, colWidths=[1.5*inch, 1*inch, 1.5*inch, 1*inch])
    perf_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), TEXT_GREY),
        ('FONT', (1, 0), (1, -1), 'Helvetica-Bold', 12),
        ('FONT', (3, 0), (3, -1), 'Helvetica-Bold', 12),
        ('TEXTCOLOR', (1, 0), (1, -1), PRIMARY_COLOR),
        ('TEXTCOLOR', (3, 0), (3, -1), PRIMARY_COLOR),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    story.append(perf_table)
    story.append(Spacer(1, 0.2*inch))
    
    # --- SECTION 3: DIFFICULTY DISTRIBUTION ---
    diff_title = Paragraph("DIFFICULTY DISTRIBUTION", section_title_style)
    story.append(diff_title)
    
    diff_data = [
        ['LEVEL', 'SOLVED', 'ATTEMPTED', 'ACCURACY'],
        ['Easy', str(easy_solved), str(easy_attempted), f"{easy_accuracy:.1f}%"],
        ['Medium', str(medium_solved), str(medium_attempted), f"{medium_accuracy:.1f}%"],
        ['Hard', str(hard_solved), str(hard_attempted), f"{hard_accuracy:.1f}%"]
    ]
    
    diff_table = Table(diff_data, colWidths=[1.2*inch, 1*inch, 1.2*inch, 1.2*inch])
    diff_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, colors.HexColor('#133a57')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ('GRID', (0, 0), (-1, -1), 0.9, colors.HexColor('#b9cfe6')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#b9cfe6')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(diff_table)
    story.append(Spacer(1, 0.2*inch))
    
    # --- SECTION 4: TOPIC PROFICIENCY ---
    topic_title = Paragraph("TOPIC PROFICIENCY", section_title_style)
    story.append(topic_title)
    
    topic_data = [['TOPIC', 'SOLVED', 'PROFICIENCY', 'TOPIC', 'SOLVED', 'PROFICIENCY']]
    
    topic_items = list(topic_stats.items())[:6]
    for i in range(0, len(topic_items), 2):
        row = []
        for j in range(2):
            if i + j < len(topic_items):
                topic, stats = topic_items[i + j]
                row.extend([topic, str(stats['solved']), stats['proficiency']])
            else:
                row.extend(['', '', ''])
        topic_data.append(row)
    
    topic_table = Table(topic_data, colWidths=[1*inch, 0.8*inch, 1.2*inch, 1*inch, 0.8*inch, 1.2*inch])
    topic_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('LINEBELOW', (0, 0), (-1, 0), 1.0, colors.HexColor('#133a57')),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (2, -1), 'CENTER'),
        ('ALIGN', (3, 1), (5, -1), 'LEFT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ('GRID', (0, 0), (-1, -1), 0.9, colors.HexColor('#b9cfe6')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#b9cfe6')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(topic_table)
    story.append(Spacer(1, 0.2*inch))
    
    # --- SECTION 5: CONTEST HISTORY ---
    contest_title = Paragraph("CONTEST HISTORY", section_title_style)
    story.append(contest_title)
    
    contest_data = [['CONTEST', 'DATE', 'SOLVED', 'RANK', 'PERCENTILE']]
    
    for contest in contest_history:
        contest_data.append([
            contest['name'],
            contest['date'],
            contest['solved'],
            contest['rank'],
            contest['percentile']
        ])
    
    if len(contest_data) == 1:
        contest_data.append(['No contest history', '', '', '', ''])
    
    contest_table = Table(contest_data, colWidths=[2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1*inch])
    contest_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('LINEBELOW', (0, 0), (-1, 0), 1.0, colors.HexColor('#133a57')),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ('GRID', (0, 0), (-1, -1), 0.9, colors.HexColor('#b9cfe6')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#b9cfe6')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(contest_table)
    story.append(Spacer(1, 0.2*inch))
    
    # --- FACULTY REMARKS ---
    remarks_title = Paragraph("FACULTY REMARKS", section_title_style)
    story.append(remarks_title)
    
    remarks_text = Paragraph(
        f"Student maintains excellent consistency. Strong in foundational data structures but needs improvement in advanced algorithms. Overall readiness for internships is high.",
        ParagraphStyle('Remarks', parent=styles['Normal'], fontSize=9, textColor=TEXT_GREY)
    )
    story.append(remarks_text)
    story.append(Spacer(1, 0.3*inch))
    
    # --- FOOTER ---
    footer_text = Paragraph(
        "<font size=8>Computer-generated document &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; CampusCode Dept.</font>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=TEXT_GREY)
    )
    story.append(footer_text)
    
    # --- BUILD PDF ---
    pdf.build(story)
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Student_Report_{user.username}_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response

@login_required
def create_thread(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        category_id = request.POST.get('category')

        ForumThread.objects.create(
            title=title,
            content=content,
            author=request.user,
            category_id=category_id if category_id else None
        )

        # XP reward for asking a question
        request.user.xp += 10
        request.user.save()

        # Update ranks since XP changed
        compute_and_update_ranks()

        return redirect('forum')

    categories = ForumCategory.objects.all()
    return render(request, 'create_thread.html', {
        'categories': categories
    })

@login_required
def forum_thread_detail(request, thread_id):
    thread = get_object_or_404(ForumThread, id=thread_id)

    # Increment views safely
    thread.views += 1
    thread.save(update_fields=['views'])

    replies = ForumReply.objects.filter(thread=thread) \
        .select_related('author') \
        .annotate(vote_count=Count('votes'))

    return render(request, 'forum_thread_detail.html', {
        'thread': thread,
        'replies': replies,
    })


@login_required
def profile(request):
    if request.method == 'POST':
        user = request.user
        new_username = request.POST.get('username')
        
        if new_username and new_username != user.username:
            if User.objects.filter(username=new_username).exists():
                messages.error(request, 'That username is already taken.')
                return redirect('profile')
            user.username = new_username

        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.college = request.POST.get('college')
        user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
        
    return render(request, 'profile.html')


@login_required
def delete_account(request):
    """Deletes the authenticated user's account.

    Requires a POST with a `confirm_username` field that matches the
    current `request.user.username` to prevent accidental deletions.
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('profile')

    user = request.user
    confirm_username = request.POST.get('confirm_username', '')

    if confirm_username != user.username:
        messages.error(request, 'Username confirmation did not match. Account not deleted.')
        return redirect('profile')

    # Logout first then delete the user (cascades to related models)
    logout(request)
    user.delete()
    messages.success(request, 'Your account has been deleted.')
    return redirect('index')


@login_required
def stats(request):
    user = request.user

    total_submissions = Submission.objects.filter(user=user).count()
    solved_problems = Submission.objects.filter(
        user=user, passed=True
    ).values('problem').distinct().count()

    success_rate = (solved_problems / total_submissions * 100) if total_submissions else 0

    difficulty_stats = {
        'Easy': Submission.objects.filter(user=user, passed=True, problem__difficulty='Easy')
            .values('problem').distinct().count(),
        'Medium': Submission.objects.filter(user=user, passed=True, problem__difficulty='Medium')
            .values('problem').distinct().count(),
        'Hard': Submission.objects.filter(user=user, passed=True, problem__difficulty='Hard')
            .values('problem').distinct().count(),
    }

    # 📈 submissions per day (last 7 days)
    daily_submissions = (
        Submission.objects.filter(user=user)
        .annotate(day=TruncDate('submitted_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    
    # Get all submissions for the table
    submissions = Submission.objects.filter(user=user).select_related('problem').order_by('-submitted_at')[:50]

    return render(request, 'report.html', {
        'total_submissions': total_submissions,
        'total_solved': solved_problems,
        'solved_problems': solved_problems,
        'success_rate': round(success_rate, 1),
        'difficulty_stats': difficulty_stats,
        'daily_submissions': list(daily_submissions),
        'submissions': submissions,
    })
   
# =========================================
# Admin Views
# =========================================

@login_required
def admin_dashboard(request):
    if request.user.role != 'Admin': return redirect('dashboard')
    stats = {
        'users': User.objects.filter(role='Student').count(),
        'problems': Problem.objects.count(),
        'contests': Contest.objects.count()
    }
    return render(request, 'admin_dashboard.html', {'stats': stats})

@login_required
def add_problem(request):
    if request.user.role != 'Admin': return redirect('dashboard')
    if request.method == 'POST':
        problem = Problem.objects.create(
            title=request.POST.get('title'),
            difficulty=request.POST.get('difficulty'),
            points=request.POST.get('points'),
            tags=request.POST.get('tags'),
            statement=request.POST.get('statement'),
            input_fmt=request.POST.get('input_fmt'),
            output_fmt=request.POST.get('output_fmt'),
            constraints=request.POST.get('constraints'),
            sample_input=request.POST.get('sample_input'),
            sample_output=request.POST.get('sample_output')
        )
        # Create a default visible test case matching the sample
        TestCase.objects.create(
            problem=problem,
            input_data=request.POST.get('sample_input'),
            expected_output=request.POST.get('sample_output'),
            is_hidden=False
        )
        messages.success(request, 'Problem Added')
    return redirect('admin_dashboard')

@login_required
def add_contest(request):
    if request.user.role != 'Admin': return redirect('dashboard')
    if request.method == 'POST':
        Contest.objects.create(
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            rules=request.POST.get('rules'),
            prizes=request.POST.get('prizes'),
            start_time=request.POST.get('start_time'),
            end_time=request.POST.get('end_time'),
            status='Upcoming'
        )
        messages.success(request, 'Contest Created')
    return redirect('admin_dashboard')

# =========================================
# Code Execution & Grading Views
# =========================================

@csrf_exempt
@login_required
def run_code(request):
    """
    Executes code against Sample Input.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST request required"}, status=400)

    try:
        data = json.loads(request.body)
        code = data.get("code")
        language = data.get("language", "python")
        user_input = data.get("stdin", "")

        payload = {
            "language": language,
            "version": "*",
            "files": [{"content": code}],
            "stdin": user_input
        }
        
        response = requests.post(PISTON_API, json=payload, timeout=5)
        result = response.json()
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@login_required
def submit_solution(request, id):
    """
    Grading Logic: Runs against ALL test cases.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        code = data.get("code")
        language = data.get("language", "python")

        problem = get_object_or_404(Problem, id=id)
        
        # [FIX 1] Use explicit filter instead of reverse relation to satisfy Pylance
        test_cases = TestCase.objects.filter(problem=problem)

        if not test_cases.exists():
            # Create a dummy object to safely run loop
            class DummyTC:
                def __init__(self, i, o): self.input_data, self.expected_output, self.is_hidden = i, o, False
            test_cases = [DummyTC(problem.sample_input, problem.sample_output)]

        results = []
        all_passed = True

        for tc in test_cases:
            payload = {
                "language": language,
                "version": "*",
                "files": [{"content": code}],
                "stdin": tc.input_data
            }

            try:
                response = requests.post(PISTON_API, json=payload, timeout=5)
                api_result = response.json()

                if 'run' not in api_result or api_result['run']['code'] != 0:
                    err_msg = api_result.get('run', {}).get('stderr', 'Unknown Error') or api_result.get('message', 'Error')
                    return JsonResponse({
                        "status": "error", 
                        "message": "Runtime/Compilation Error",
                        "details": err_msg
                    })

                # [FIX 2] Handle NoneType for stdout/expected output using (var or "")
                actual_output = (api_result['run'].get('stdout') or "").strip()
                expected_output = (tc.expected_output or "").strip()

                if actual_output == expected_output:
                    results.append({"status": "Passed"})
                else:
                    all_passed = False
                    results.append({
                        "status": "Failed",
                        "input": "Hidden Test Case" if tc.is_hidden else tc.input_data,
                        "expected": "Hidden" if tc.is_hidden else expected_output,
                        "actual": actual_output
                    })
                    break 

            except Exception as e:
                return JsonResponse({"status": "error", "message": "Execution API Failed", "details": str(e)})

        if all_passed:
            has_solved = Submission.objects.filter(user=request.user, problem=problem, passed=True).exists()
            msg = "Correct Answer!"
            
            if not has_solved:
                request.user.xp += problem.points
                request.user.save()
                msg += f" You earned +{problem.points} XP."

                # Update ranks since XP changed
                compute_and_update_ranks()
            
            Submission.objects.create(user=request.user, problem=problem, code=code, passed=True)
            return JsonResponse({"status": "success", "message": msg})
        else:
            Submission.objects.create(user=request.user, problem=problem, code=code, passed=False)
            return JsonResponse({"status": "failed", "results": results})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)