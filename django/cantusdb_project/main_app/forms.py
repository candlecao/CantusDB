from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import (
    Chant,
    Office,
    Genre,
    Notation,
    Feast,
    Source,
    RismSiglum,
    Segment,
    Provenance,
    Century,
    Sequence,
    Differentia,
)
from .widgets import (
    TextInputWidget,
    VolpianoInputWidget,
    TextAreaWidget,
    VolpianoAreaWidget,
    SelectWidget,
    CheckboxWidget,
)
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.contrib.admin.widgets import (
    FilteredSelectMultiple,
)
from dal import autocomplete

# ModelForm allows to build a form directly from a model
# see https://docs.djangoproject.com/en/3.0/topics/forms/modelforms/

"""
# 3 ways of doing it
#1 worst, helptext in the model will be missing
class CommetnForm(forms.Form):
    marginalia = forms.CharField(
        label="Marginalia", widget=forms.TextInput(), help_text="help"
    )
    url = forms.URLField()
    comment = forms.CharField()

    url.widget.attrs.update({'class': 'special'})
    comment.widget.attrs.update(size='40')
#2
class CommentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'special'})
        self.fields['comment'].widget.attrs.update(size='40')
"""


class NameModelChoiceField(forms.ModelChoiceField):
    """
    A custom ModelChoiceField that overrides the label_from_instance method
    to display the object's name attribute instead of str(object).
    This field is specifically designed for handling genre and office objects.
    Rather than displaying the name along with its description, sometimes we
    only want the shorthand notation for the genre and office objects.
    (Eg. [AV] Antiphon verse --> AV)
    """

    def label_from_instance(self, obj):
        return obj.name


# 3 best
class ChantCreateForm(forms.ModelForm):
    class Meta:
        model = Chant
        # specify either 'fields' or 'excludes' so that django knows which fields to use
        fields = [
            "marginalia",
            "folio",
            "c_sequence",
            "office",
            "genre",
            "position",
            "cantus_id",
            "feast",
            "mode",
            "differentia",
            "diff_db",
            "finalis",
            "extra",
            "chant_range",
            "manuscript_full_text_std_spelling",
            "manuscript_full_text",
            "volpiano",
            "image_link",
            "melody_id",
            "content_structure",
            "indexing_notes",
            "addendum",
        ]
        # the widgets dictionary is ignored for a model field with a non-empty
        # choices attribute. In this case, you must override the form field to
        # use a different widget. this goes for all foreignkey and required fields
        # here, which are written explicitly below to override form field
        widgets = {
            "marginalia": TextInputWidget(),
            # folio: defined below (required)
            # c_sequence: defined below (required)
            "office": autocomplete.ModelSelect2(url="office-autocomplete"),
            "genre": autocomplete.ModelSelect2(url="genre-autocomplete"),
            "position": TextInputWidget(),
            "cantus_id": TextInputWidget(),
            "feast": autocomplete.ModelSelect2(url="feast-autocomplete"),
            "mode": TextInputWidget(),
            "differentia": TextInputWidget(),
            "diff_db": autocomplete.ModelSelect2(url="differentia-autocomplete"),
            "finalis": TextInputWidget(),
            "extra": TextInputWidget(),
            "chant_range": VolpianoInputWidget(),
            # manuscript_full_text_std_spelling: defined below (required)
            "manuscript_full_text": TextAreaWidget(),
            "volpiano": VolpianoAreaWidget(),
            "image_link": TextInputWidget(),
            "melody_id": TextInputWidget(),
            "content_structure": TextInputWidget(),
            "indexing_notes": TextAreaWidget(),
            "addendum": TextInputWidget(),
        }

    folio = forms.CharField(
        required=True,
        widget=TextInputWidget,
        help_text="Binding order",
    )

    c_sequence = forms.CharField(
        required=True,
        widget=TextInputWidget,
        help_text="Each folio starts with '1'.",
    )

    manuscript_full_text_std_spelling = forms.CharField(
        required=True,
        widget=TextAreaWidget,
        help_text="Manuscript full text with standardized spelling. Enter the words "
        "according to the manuscript but normalize their spellings following "
        "Classical Latin forms. Use upper-case letters for proper nouns, "
        'the first word of each chant, and the first word after "Alleluia" for '
        "Mass Alleluias. Punctuation is omitted.",
    )

    # automatically computed fields
    # source and incipit are mandatory fields in model,
    # but have to be optional in the form, otherwise the field validation won't pass
    source = forms.ModelChoiceField(
        queryset=Source.objects.all().order_by("title"),
        required=False,
        error_messages={
            "invalid_choice": "This source does not exist, please switch to a different source."
        },
    )
    incipit = forms.CharField(required=False)


class SourceCreateForm(forms.ModelForm):
    class Meta:
        model = Source
        fields = [
            "title",
            "rism_siglum",
            "siglum",
            "provenance",
            "provenance_notes",
            "full_source",
            "date",
            "century",
            "cursus",
            "current_editors",
            "melodies_entered_by",
            "inventoried_by",
            "full_text_entered_by",
            "proofreaders",
            "other_editors",
            "complete_inventory",
            "summary",
            "description",
            "selected_bibliography",
            "image_link",
            "fragmentarium_id",
            "dact_id",
            "indexing_notes",
        ]
        widgets = {
            "title": TextInputWidget(),
            "siglum": TextInputWidget(),
            "provenance": autocomplete.ModelSelect2(url="provenance-autocomplete"),
            "provenance_notes": TextInputWidget(),
            "date": TextInputWidget(),
            "cursus": SelectWidget(),
            "summary": TextAreaWidget(),
            "description": TextAreaWidget(),
            "selected_bibliography": TextAreaWidget(),
            "image_link": TextInputWidget(),
            "fragmentarium_id": TextInputWidget(),
            "dact_id": TextInputWidget(),
            "indexing_notes": TextAreaWidget(),
            "rism_siglum": autocomplete.ModelSelect2(url="rismsiglum-autocomplete"),
            "current_editors": autocomplete.ModelSelect2Multiple(
                url="current-editors-autocomplete"
            ),
            "melodies_entered_by": autocomplete.ModelSelect2Multiple(
                url="all-users-autocomplete"
            ),
            "century": autocomplete.ModelSelect2Multiple(url="century-autocomplete"),
            "inventoried_by": autocomplete.ModelSelect2Multiple(
                url="all-users-autocomplete"
            ),
            "full_text_entered_by": autocomplete.ModelSelect2Multiple(
                url="all-users-autocomplete"
            ),
            "proofreaders": autocomplete.ModelSelect2Multiple(
                url="all-users-autocomplete"
            ),
            "other_editors": autocomplete.ModelSelect2Multiple(
                url="all-users-autocomplete"
            ),
        }

    TRUE_FALSE_CHOICES_SOURCE = (
        (True, "Full source"),
        (False, "Fragment or Fragmented"),
    )

    full_source = forms.ChoiceField(choices=TRUE_FALSE_CHOICES_SOURCE, required=False)
    full_source.widget.attrs.update(
        {"class": "form-control custom-select custom-select-sm"}
    )
    TRUE_FALSE_CHOICES_INVEN = ((True, "Complete"), (False, "Incomplete"))

    complete_inventory = forms.ChoiceField(
        choices=TRUE_FALSE_CHOICES_INVEN, required=False
    )
    complete_inventory.widget.attrs.update(
        {"class": "form-control custom-select custom-select-sm"}
    )


class ChantEditForm(forms.ModelForm):
    class Meta:
        model = Chant
        fields = [
            "manuscript_full_text_std_spelling",
            "manuscript_full_text",
            "volpiano",
            "marginalia",
            "folio",
            "c_sequence",
            "feast",
            "office",
            "genre",
            "position",
            "cantus_id",
            "melody_id",
            "mode",
            "finalis",
            "differentia",
            "diff_db",
            "extra",
            "image_link",
            "indexing_notes",
            "addendum",
            "chant_range",
            "manuscript_full_text_std_proofread",
            "manuscript_full_text_proofread",
            "volpiano_proofread",
            "proofread_by",
        ]
        widgets = {
            # manuscript_full_text_std_spelling: defined below (required)
            "manuscript_full_text": TextAreaWidget(),
            "volpiano": VolpianoAreaWidget(),
            "marginalia": TextInputWidget(),
            # folio: defined below (required)
            # c_sequence: defined below (required)
            "feast": autocomplete.ModelSelect2(url="feast-autocomplete"),
            "office": autocomplete.ModelSelect2(url="office-autocomplete"),
            "genre": autocomplete.ModelSelect2(url="genre-autocomplete"),
            "position": TextInputWidget(),
            "cantus_id": TextInputWidget(),
            "melody_id": TextInputWidget(),
            "mode": TextInputWidget(),
            "finalis": TextInputWidget(),
            "differentia": TextInputWidget(),
            "diff_db": autocomplete.ModelSelect2(url="differentia-autocomplete"),
            "extra": TextInputWidget(),
            "image_link": TextInputWidget(),
            "indexing_notes": TextAreaWidget(),
            "addendum": TextInputWidget(),
            "chant_range": VolpianoAreaWidget(),
            "manuscript_full_text_std_proofread": CheckboxWidget(),
            "manuscript_full_text_proofread": CheckboxWidget(),
            "volpiano_proofread": CheckboxWidget(),
            "proofread_by": autocomplete.ModelSelect2Multiple(
                url="proofread-by-autocomplete"
            ),
        }

    manuscript_full_text_std_spelling = forms.CharField(
        required=True,
        widget=TextAreaWidget,
        help_text="Manuscript full text with standardized spelling. Enter the words "
        "according to the manuscript but normalize their spellings following "
        "Classical Latin forms. Use upper-case letters for proper nouns, "
        'the first word of each chant, and the first word after "Alleluia" for '
        "Mass Alleluias. Punctuation is omitted.",
    )

    folio = forms.CharField(
        required=True,
        widget=TextInputWidget,
        help_text="Binding order",
    )

    c_sequence = forms.CharField(
        required=True,
        widget=TextInputWidget,
        help_text="Each folio starts with '1'.",
    )


class SourceEditForm(forms.ModelForm):
    class Meta:
        model = Source
        fields = [
            "title",
            "rism_siglum",
            "siglum",
            "provenance",
            "provenance_notes",
            "full_source",
            "date",
            "century",
            "cursus",
            "complete_inventory",
            "summary",
            "liturgical_occasions",
            "description",
            "selected_bibliography",
            "image_link",
            "fragmentarium_id",
            "dact_id",
            "indexing_notes",
            "current_editors",
            "melodies_entered_by",
            "inventoried_by",
            "full_text_entered_by",
            "proofreaders",
            "other_editors",
        ]
        widgets = {
            "title": TextInputWidget(),
            "rism_siglum": autocomplete.ModelSelect2(url="rismsiglum-autocomplete"),
            "siglum": TextInputWidget(),
            "provenance": autocomplete.ModelSelect2(url="provenance-autocomplete"),
            "provenance_notes": TextInputWidget(),
            "date": TextInputWidget(),
            "summary": TextAreaWidget(),
            "liturgical_occasions": TextAreaWidget(),
            "description": TextAreaWidget(),
            "selected_bibliography": TextAreaWidget(),
            "image_link": TextInputWidget(),
            "fragmentarium_id": TextInputWidget(),
            "dact_id": TextInputWidget(),
            "indexing_notes": TextAreaWidget(),
            "current_editors": autocomplete.ModelSelect2Multiple(
                url="current-editors-autocomplete"
            ),
            "melodies_entered_by": autocomplete.ModelSelect2Multiple(
                url="all-users-autocomplete"
            ),
            "century": autocomplete.ModelSelect2Multiple(url="century-autocomplete"),
            "inventoried_by": autocomplete.ModelSelect2Multiple(
                url="all-users-autocomplete"
            ),
            "full_text_entered_by": autocomplete.ModelSelect2Multiple(
                url="all-users-autocomplete"
            ),
            "proofreaders": autocomplete.ModelSelect2Multiple(
                url="all-users-autocomplete"
            ),
            "other_editors": autocomplete.ModelSelect2Multiple(
                url="all-users-autocomplete"
            ),
        }

    CHOICES_FULL_SOURCE = (
        (None, "None"),
        (True, "Full source"),
        (False, "Fragment or Fragmented"),
    )
    full_source = forms.ChoiceField(choices=CHOICES_FULL_SOURCE, required=False)
    full_source.widget.attrs.update(
        {"class": "form-control custom-select custom-select-sm"}
    )

    CHOICES_CURSUS = (
        (None, "None"),
        ("Monastic", "Monastic"),
        ("Secular", "Secular"),
    )
    cursus = forms.ChoiceField(choices=CHOICES_CURSUS, required=False)
    cursus.widget.attrs.update({"class": "form-control custom-select custom-select-sm"})

    CHOICES_COMPLETE_INV = (
        (True, "complete inventory"),
        (False, "partial inventory"),
    )
    complete_inventory = forms.ChoiceField(choices=CHOICES_COMPLETE_INV, required=False)
    complete_inventory.widget.attrs.update(
        {"class": "form-control custom-select custom-select-sm"}
    )


class SequenceEditForm(forms.ModelForm):
    class Meta:
        model = Sequence
        fields = [
            "title",
            "siglum",
            "incipit",
            "folio",
            "s_sequence",
            "genre",
            "rubrics",
            "analecta_hymnica",
            "indexing_notes",
            "date",
            "col1",
            "col2",
            "col3",
            "ah_volume",
            "source",
            "cantus_id",
            "image_link",
        ]
        widgets = {
            "title": TextInputWidget(),
            "siglum": TextInputWidget(),
            "incipit": TextInputWidget(),
            "folio": TextInputWidget(),
            "s_sequence": TextInputWidget(),
            "rubrics": TextInputWidget(),
            "analecta_hymnica": TextInputWidget(),
            "indexing_notes": TextAreaWidget(),
            "date": TextInputWidget(),
            "col1": TextInputWidget(),
            "col2": TextInputWidget(),
            "col3": TextInputWidget(),
            "ah_volume": TextInputWidget(),
            "cantus_id": TextInputWidget(),
            "image_link": TextInputWidget(),
        }

    # We use NameModelChoiceField here so the dropdown list of genres displays the name
    # instead of [name] + description
    genre = NameModelChoiceField(
        queryset=Genre.objects.all().order_by("name"), required=False
    )
    genre.widget.attrs.update({"class": "form-control custom-select custom-select-sm"})

    source = forms.ModelChoiceField(
        queryset=Source.objects.all().order_by("title"), required=False
    )
    source.widget.attrs.update({"class": "form-control custom-select custom-select-sm"})


class ChantEditSyllabificationForm(forms.ModelForm):
    class Meta:
        model = Chant
        fields = [
            "manuscript_full_text",
            "manuscript_syllabized_full_text",
        ]
        widgets = {
            "manuscript_full_text": TextAreaWidget(),
            "manuscript_syllabized_full_text": TextAreaWidget(),
        }


class AdminCenturyForm(forms.ModelForm):
    class Meta:
        model = Century
        fields = "__all__"

    name = forms.CharField(required=True, widget=TextInputWidget)


class AdminChantForm(forms.ModelForm):
    class Meta:
        model = Chant
        fields = "__all__"
        widgets = {
            "volpiano": VolpianoAreaWidget(),
            "indexing_notes": TextAreaWidget(),
            "manuscript_full_text_std_proofread": CheckboxWidget(),
            "manuscript_full_text_proofread": CheckboxWidget(),
            "volpiano_proofread": CheckboxWidget(),
            "chant_range": VolpianoAreaWidget(),
        }

    manuscript_full_text_std_spelling = forms.CharField(
        required=True,
        widget=TextAreaWidget,
        help_text="Manuscript full text with standardized spelling. Enter the words "
        "according to the manuscript but normalize their spellings following "
        "Classical Latin forms. Use upper-case letters for proper nouns, "
        'the first word of each chant, and the first word after "Alleluia" for '
        "Mass Alleluias. Punctuation is omitted.",
    )
    # Django's default text area widget selection for form inputs is non-intuitive
    # and manual updates to fields (e.g., changing required=True) affect widget properties unexpectedly;
    # this workaround is our current best solution.
    manuscript_full_text_std_spelling.widget.attrs.update(
        {"style": "width: 610px; height: 170px;"}
    )

    folio = forms.CharField(
        required=True,
        widget=TextInputWidget,
        help_text="Binding order",
    )

    c_sequence = forms.CharField(
        required=True,
        widget=TextInputWidget,
        help_text="Each folio starts with '1'.",
        label="Sequence",
    )

    # We use NameModelChoiceField here so the dropdown list of office/mass displays the name
    # instead of [name] + description
    office = NameModelChoiceField(
        queryset=Office.objects.all().order_by("name"),
        required=False,
    )
    # We use NameModelChoiceField here so the dropdown list of genres displays the name
    # instead of [name] + description
    genre = NameModelChoiceField(
        queryset=Genre.objects.all().order_by("name"), required=False
    )

    proofread_by = forms.ModelMultipleChoiceField(
        queryset=get_user_model()
        .objects.filter(Q(groups__name="project manager") | Q(groups__name="editor"))
        .distinct()
        .order_by("last_name"),
        required=False,
        widget=FilteredSelectMultiple(verbose_name="proofread by", is_stacked=False),
    )


class AdminFeastForm(forms.ModelForm):
    class Meta:
        model = Feast
        fields = "__all__"

    name = forms.CharField(required=True, widget=TextInputWidget)


class AdminGenreForm(forms.ModelForm):
    class Meta:
        model = Genre
        fields = "__all__"

    name = forms.CharField(required=True, widget=TextInputWidget)
    description = forms.CharField(required=True, widget=TextAreaWidget)


class AdminNotationForm(forms.ModelForm):
    class Meta:
        model = Notation
        fields = "__all__"

    name = forms.CharField(required=True, widget=TextInputWidget)
    name.widget.attrs.update({"style": "width: 400px;"})


class AdminOfficeForm(forms.ModelForm):
    class Meta:
        model = Office
        fields = "__all__"

    name = forms.CharField(required=True, widget=TextInputWidget)
    description = forms.CharField(required=True, widget=TextAreaWidget)


class AdminProvenanceForm(forms.ModelForm):
    class Meta:
        model = Provenance
        fields = "__all__"

    name = forms.CharField(required=True, widget=TextInputWidget)


class AdminRismSiglumForm(forms.ModelForm):
    class Meta:
        model = RismSiglum
        fields = "__all__"

    name = forms.CharField(required=True, widget=TextInputWidget)


class AdminSegmentForm(forms.ModelForm):
    class Meta:
        model = Segment
        fields = "__all__"

    name = forms.CharField(required=True, widget=TextInputWidget)
    name.widget.attrs.update({"style": "width: 400px;"})


class AdminSequenceForm(forms.ModelForm):
    class Meta:
        model = Sequence
        fields = "__all__"
        widgets = {
            "volpiano": VolpianoAreaWidget(),
            "indexing_notes": TextAreaWidget(),
            "manuscript_full_text_std_proofread": CheckboxWidget(),
            "manuscript_full_text_proofread": CheckboxWidget(),
            "volpiano_proofread": CheckboxWidget(),
            "chant_range": VolpianoAreaWidget(),
        }

    # We use NameModelChoiceField here so the dropdown list of office/mass displays the name
    # instead of [name] + description
    office = NameModelChoiceField(
        queryset=Office.objects.all().order_by("name"),
        required=False,
    )
    # We use NameModelChoiceField here so the dropdown list of genres displays the name
    # instead of [name] + description
    genre = NameModelChoiceField(
        queryset=Genre.objects.all().order_by("name"), required=False
    )

    proofread_by = forms.ModelMultipleChoiceField(
        queryset=get_user_model()
        .objects.filter(Q(groups__name="project manager") | Q(groups__name="editor"))
        .distinct()
        .order_by("last_name"),
        required=False,
        widget=FilteredSelectMultiple(verbose_name="proofread by", is_stacked=False),
    )


class AdminSourceForm(forms.ModelForm):
    class Meta:
        model = Source
        fields = "__all__"

    title = forms.CharField(
        required=True,
        widget=TextInputWidget,
        help_text="Full Manuscript Identification (City, Archive, Shelf-mark)",
    )
    title.widget.attrs.update({"style": "width: 610px;"})

    siglum = forms.CharField(
        required=True,
        widget=TextInputWidget,
        help_text="RISM-style siglum + Shelf-mark (e.g. GB-Ob 202).",
    )

    rism_siglum = forms.ModelChoiceField(
        queryset=RismSiglum.objects.all().order_by("name"),
        required=False,
    )

    provenance = forms.ModelChoiceField(
        queryset=Provenance.objects.all().order_by("name"),
        required=False,
    )
    TRUE_FALSE_CHOICES_SOURCE = (
        (True, "Full source"),
        (False, "Fragment or Fragmented"),
    )

    full_source = forms.ChoiceField(choices=TRUE_FALSE_CHOICES_SOURCE, required=False)

    century = forms.ModelMultipleChoiceField(
        queryset=Century.objects.all().order_by("name"),
        required=False,
        widget=FilteredSelectMultiple(verbose_name="Century", is_stacked=False),
    )

    current_editors = forms.ModelMultipleChoiceField(
        queryset=get_user_model()
        .objects.filter(
            Q(groups__name="project manager")
            | Q(groups__name="editor")
            | Q(groups__name="contributor")
        )
        .distinct()
        .order_by("full_name"),
        required=False,
        widget=FilteredSelectMultiple(verbose_name="current editors", is_stacked=False),
    )

    inventoried_by = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.all().order_by("full_name"),
        required=False,
        widget=FilteredSelectMultiple(verbose_name="inventoried by", is_stacked=False),
    )

    full_text_entered_by = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.all().order_by("full_name"),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name="full text entered by", is_stacked=False
        ),
    )

    melodies_entered_by = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.all().order_by("full_name"),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name="melodies entered by", is_stacked=False
        ),
    )

    proofreaders = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.all().order_by("full_name"),
        required=False,
        widget=FilteredSelectMultiple(verbose_name="proofreaders", is_stacked=False),
    )

    other_editors = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.all().order_by("full_name"),
        required=False,
        widget=FilteredSelectMultiple(verbose_name="other editors", is_stacked=False),
    )

    TRUE_FALSE_CHOICES_INVEN = ((True, "Complete"), (False, "Incomplete"))

    complete_inventory = forms.ChoiceField(
        choices=TRUE_FALSE_CHOICES_INVEN, required=False
    )


class AdminUserChangeForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = "__all__"

    email = forms.CharField(
        required=True,
        widget=TextInputWidget,
    )
    email.widget.attrs.update({"style": "width: 300px;"})

    password = ReadOnlyPasswordHashField(
        help_text=(
            "Raw passwords are not stored, so there is no way to see "
            "this user's password, but you can change the password "
            'using <a href="../password/">this form</a>.'
        )
    )
