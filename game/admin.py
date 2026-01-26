from django.contrib import admin
from .models import (
    DialogueTree, DialogueNode, PractitionerChoice, 
    Scenario, MIQuestion, ModuleProgress, UserScore
)

class PractitionerChoiceInline(admin.TabularInline):
    model = PractitionerChoice
    extra = 4

@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ('module_number', 'title', 'scenario_type', 'difficulty')
    search_fields = ('title', 'description')

@admin.register(DialogueTree)
class DialogueTreeAdmin(admin.ModelAdmin):
    list_display = ('module_number', 'title', 'technique_focus', 'stage_of_change')
    list_filter = ('module_number', 'stage_of_change')
    search_fields = ('title', 'learning_objective', 'technique_focus')

@admin.register(DialogueNode)
class DialogueNodeAdmin(admin.ModelAdmin):
    list_display = ('tree', 'node_id', 'change_talk_present', 'is_ending')
    list_filter = ('tree', 'change_talk_present', 'is_ending')
    search_fields = ('patient_statement', 'patient_context')
    inlines = [PractitionerChoiceInline]

@admin.register(ModuleProgress)
class ModuleProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'scenario', 'completion_status', 'completion_score')
    list_filter = ('completion_status', 'scenario')
    search_fields = ('user__username', 'scenario__title')

@admin.register(UserScore)
class UserScoreAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_points', 'scenarios_completed', 'modules_completed')
    search_fields = ('user__username',)
    readonly_fields = ('total_points', 'technique_mastery', 'change_talk_evoked')