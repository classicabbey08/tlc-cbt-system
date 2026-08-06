from django import forms
from django.forms import inlineformset_factory

from .models import Choice, Exam, Question, Subject


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
        }


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = [
            'subject',
            'title',
            'target_class',
            'duration_minutes',
            'is_active',
        ]

        widgets = {
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'target_class': forms.Select(attrs={'class': 'form-select'}),
            'duration_minutes': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 1}
            ),
            'is_active': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)

        if teacher is not None:
            if getattr(teacher, 'is_super_admin', False):
                self.fields['subject'].queryset = Subject.objects.all().order_by('name')
            else:
                self.fields['subject'].queryset = Subject.objects.filter(
                    created_by=teacher
                ).order_by('name')


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'marks']
        widgets = {
            'text': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
            'marks': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 1}
            ),
        }


class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['text', 'is_correct']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_correct': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
        }


ChoiceFormSet = inlineformset_factory(
    Question,
    Choice,
    form=ChoiceForm,
    extra=4,
    min_num=4,
    max_num=4,
    validate_min=True,
    validate_max=True,
    can_delete=False,
)