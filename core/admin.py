from django.contrib import admin
from .models import (
    User,
    Problem,
    Contest,
    ForumCategory,
    ForumThread,
    ForumReply,
    ForumVote,
)


admin.site.register(User)
admin.site.register(Problem)
admin.site.register(Contest)
admin.site.register(ForumCategory)
admin.site.register(ForumThread)
admin.site.register(ForumReply)
admin.site.register(ForumVote)
