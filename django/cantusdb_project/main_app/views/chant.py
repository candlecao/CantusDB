import lxml.html as lh
import requests
from django.contrib import messages
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Q, QuerySet
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from main_app.forms import ChantCreateForm
from main_app.models import Chant, Feast, Genre, Source


def keyword_search(queryset: QuerySet, keywords: str) -> QuerySet:
    """
    Performs a keyword search over a QuerySet

    Uses PostgreSQL's full text search features

    Args:
        queryset (QuerySet): A QuerySet to be searched
        keywords (str): A string of keywords to search the QuerySet

    Returns:
        QuerySet: A QuerySet filtered by keywords
    """
    query = SearchQuery(keywords)
    rank_annotation = SearchRank(F("search_vector"), query)
    filtered_queryset = (
        queryset.annotate(rank=rank_annotation)
        .filter(search_vector=query)
        .order_by("-rank")
    )
    return filtered_queryset


class ChantDetailView(DetailView):
    """
    Displays a single Chant object. Accessed with ``chants/<int:pk>``
    """

    model = Chant
    context_object_name = "chant"
    template_name = "chant_detail.html"


class ChantListView(ListView):
    """
    Displays a list of Chant objects. Accessed with ``chants/``
    """

    model = Chant
    queryset = Chant.objects.all().order_by("id")
    paginate_by = 18
    context_object_name = "chants"
    template_name = "chant_list.html"


class ChantSearchView(ListView):
    """
    Searches Chants and displays them as a list, accessed with ``chant-search/``

    If no ``GET`` parameters, returns all chants

    ``GET`` parameters:
        ``genre``: Filters by Genre of Chant
        ``cantus_id``: Filters by the Cantus ID field of Chant
        ``mode``: Filters by mode of Chant
        ``melodies``: Filters Chant by whether or not it contains a melody in
                      Volpiano form. Valid values are "true" or "false".
        ``feast``: Filters by Feast of Chant
        ``incipit``: Searches text of Chant for keywords
    """

    model = Chant
    queryset = Chant.objects.all().order_by("id")
    paginate_by = 100
    context_object_name = "chants"
    template_name = "chant_search.html"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        # Add to context a QuerySet of dicts with id and name of each Genre
        context["genres"] = (
            Genre.objects.all().order_by("name").values("id", "name")
        )
        return context

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        # Create a Q object to filter the QuerySet of Chants
        q_obj_filter = Q()

        # For every GET parameter other than incipit, add to the Q object
        if self.request.GET.get("genre"):
            genre_id = int(self.request.GET.get("genre"))
            q_obj_filter &= Q(genre__id=genre_id)
        if self.request.GET.get("cantus_id"):
            cantus_id = self.request.GET.get("cantus_id")
            q_obj_filter &= Q(cantus_id=cantus_id)
        if self.request.GET.get("mode"):
            mode = self.request.GET.get("mode")
            q_obj_filter &= Q(mode=mode)
        if self.request.GET.get("melodies") in ["true", "false"]:
            melodies = self.request.GET.get("melodies")
            if melodies == "true":
                q_obj_filter &= Q(volpiano__isnull=False)
            if melodies == "false":
                q_obj_filter &= Q(volpiano__isnull=True)
        if self.request.GET.get("feast"):
            feast = self.request.GET.get("feast")
            feast = Feast.objects.filter(name=feast)
            q_obj_filter &= Q(feast__in=feast)

        # Filter the QuerySet with Q object
        queryset = queryset.filter(q_obj_filter)

        # Finally, use the incipit parameter to do keyword searching
        # over the QuerySet
        if self.request.GET.get("keyword"):
            incipit = self.request.GET.get("keyword")
            queryset = keyword_search(queryset, incipit)

        return queryset


class ChantCreateView(CreateView):
    """Create chant at /chant-create/<source-id>
    """

    model = Chant
    template_name = "input_form_w.html"
    form_class = ChantCreateForm
    # if success_url and get_success_url not specified, will direct to chant detail page
    def get_success_url(self):
        return reverse("chant-create", args=[self.source.id])

    def get_initial(self):
        (
            self.latest_folio,
            self.latest_feast,
            self.latest_seq,
        ) = self.get_folio_feast_seq()
        return {
            "folio": self.latest_folio,
            "feast": self.latest_feast,
            "sequence_number": self.latest_seq,
        }

    def get_folio_feast_seq(self):
        """get the default [folio, feast, seq] from the last created chant
        last created chant is found using 'date-updated'
        """
        chants_in_source = (
            Chant.objects.all()
            .filter(source=self.source)
            .order_by("-date_updated")
        )
        if not chants_in_source:
            # if there is no chant in source
            latest_folio = "001r"
            latest_feast = ""
            latest_seq = 0
        else:
            latest_chant = chants_in_source[0]
            if latest_chant.folio:
                latest_folio = latest_chant.folio
            else:
                latest_folio = "001r"
            if latest_chant.feast:
                latest_feast = latest_chant.feast.id
            else:
                latest_feast = ""
            if latest_chant.sequence_number:
                latest_seq = latest_chant.sequence_number
            else:
                latest_seq = 0
        return latest_folio, latest_feast, latest_seq + 1

    def dispatch(self, request, *args, **kwargs):
        """Make sure the source specified in url exists before we display the form
        """
        self.source = get_object_or_404(Source, pk=kwargs["source_pk"])
        self.source_id = kwargs["source_pk"]
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["source_link"] = reverse(
            "source-detail", args=[self.source_id]
        )
        context["source"] = self.source
        try:
            previous_chant = Chant.objects.all().get(
                source=self.source,
                folio=self.latest_folio,
                sequence_number=self.latest_seq - 1,
            )
            context["previous_chant"] = previous_chant
            context["previous_chant_link"] = reverse(
                "chant-detail", args=[previous_chant.id]
            )
        except Chant.DoesNotExist:
            context["previous_chant"] = None

        return context

    def form_valid(self, form):
        """compute source, incipit; folio/sequence (if left empty)
        validate the form: add success/error message
        """
        # compute source
        form.instance.source = self.source  # same effect as the next line
        # form.instance.source = get_object_or_404(Source, pk=self.kwargs['source_pk'])

        # compute incipit, within 30 charactors, keep words complete
        words = form.instance.manuscript_full_text_std_spelling.split(" ")
        incipit = ""
        for word in words:
            new_incipt = incipit + word + " "
            if len(new_incipt) >= 30:
                break
            incipit = new_incipt
        form.instance.incipit = incipit.strip(" ")

        # if the folio field is left empty
        if form.instance.folio is None:
            form.instance.folio = self.latest_folio

        # if the sequence field is left empty
        if form.instance.sequence_number is None:
            form.instance.sequence_number = self.latest_seq

        # if a chant with the same sequence and folio already exists in the source
        if (
            Chant.objects.all()
            .filter(
                source=self.source,
                folio=form.instance.folio,
                sequence_number=form.instance.sequence_number,
            )
            .exists()
        ):
            form.add_error(
                None,
                "Chant with the same sequence and folio already exists in this source.",
            )

        if form.is_valid():
            messages.success(
                self.request,
                "Chant '" + form.instance.incipit + "' created successfully!",
            )
            return super().form_valid(form)
        else:
            return super().form_invalid(form)


class ChantDeleteView(DeleteView):
    """delete chant on chant-detail page
    """

    model = Chant
    success_url = reverse_lazy("chant-list")
    template_name = "chant_confirm_delete.html"


class ChantUpdateView(UpdateView):
    model = Chant
    template_name = "chant_form.html"
    fields = "__all__"
    success_url = "/chants"


class CISearchView(TemplateView):
    """search in CI and write results in get_context_data
    """

    template_name = "ci_search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_term = kwargs["search_term"]
        search_term = search_term.replace(" ", "+")  # for multiple keywords
        # Create empty list for the 3 types of info
        cantus_id = []
        genre = []
        full_text = []

        # scrape multiple pages
        pages = range(0, 5)
        for page in pages:
            p = {
                "t": search_term,
                "cid": "",
                "genre": "All",
                "ghisp": "All",
                "page": page,
            }
            page = requests.get("http://cantusindex.org/search", params=p)
            doc = lh.fromstring(page.content)
            # Parse data that are stored between <tr>..</tr> of HTML
            tr_elements = doc.xpath("//tr")
            # if cantus index returns an empty table
            if not tr_elements:
                break

            # remove the table header
            tr_elements = tr_elements[1:]

            for row in tr_elements:
                cantus_id.append(row[0].text_content().strip())
                genre.append(row[1].text_content().strip())
                full_text.append(row[2].text_content().strip())

        # for looping through three lists in template, we have to zip it here
        if len(cantus_id) == 0:
            context["results"] = [["No results", "No results", "No results"]]
        else:
            context["results"] = zip(cantus_id, genre, full_text)
        return context
