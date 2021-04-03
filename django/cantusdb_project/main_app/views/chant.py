from django.views.generic import (
    DetailView,
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
)
from django.db.models import Q
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy

import requests
import lxml.html as lh
import json

from main_app.models import Chant, Genre, Feast, Source
from main_app.forms import ChantCreateForm


class ChantDetailView(DetailView):
    model = Chant
    context_object_name = "chant"
    template_name = "chant_detail.html"


class ChantListView(ListView):
    model = Chant
    queryset = Chant.objects.all().order_by("id")
    paginate_by = 18
    context_object_name = "chants"
    template_name = "chant_list.html"


class ChantSearchView(ListView):
    model = Chant
    queryset = Chant.objects.all().order_by("id")
    paginate_by = 100
    context_object_name = "chants"
    template_name = "chant_search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["genres"] = Genre.objects.all().order_by("name").values("id", "name")
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        q_obj_filter = Q()
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
            q_obj_filter &= Q(feast=feast)
        if self.request.GET.get("incipit"):
            # Make list of terms split on spaces
            incipit_terms = self.request.GET.get("incipit").split(" ")
            incipit_q = Q()
            # For each term, add it to the Q object of each field with an OR operation.
            # We split the terms so that the words can be separated in the actual
            # field, allowing for a more flexible search, and a field needs
            # to match only one of the terms
            for term in incipit_terms:
                incipit_q |= Q(incipit__icontains=term)
            q_obj_filter &= incipit_q
        return queryset.filter(q_obj_filter)


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
            self.latest_image,
        ) = self.get_folio_feast_seq_image()
        return {
            "folio": self.latest_folio,
            "feast": self.latest_feast,
            "sequence_number": self.latest_seq,
            "image_link": self.latest_image,
        }

    def get_folio_feast_seq_image(self):
        """get the default [folio, feast, seq] from the last created chant
        last created chant is found using 'date-updated'
        """
        chants_in_source = (
            Chant.objects.all().filter(source=self.source).order_by("-date_updated")
        )
        if not chants_in_source:
            # if there is no chant in source
            latest_folio = "001r"
            latest_feast = ""
            latest_seq = 0
            latest_image = ""
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
            if latest_chant.image_link:
                latest_image = latest_chant.image_link
            else:
                latest_image = ""
        return latest_folio, latest_feast, latest_seq + 1, latest_image

    def dispatch(self, request, *args, **kwargs):
        """Make sure the source specified in url exists before we display the form
        """
        self.source = get_object_or_404(Source, pk=kwargs["source_pk"])
        self.source_id = kwargs["source_pk"]
        return super().dispatch(request, *args, **kwargs)

    def get_suggested_chants(self):
        """get suggested chants based on the previous chant entered
        look for the CantusID of the previous chant in any source,
        compile a list of all the chants (CantusIDs) that follow it (use seq) on the same or the next folio,
        using these CantusIDs, search in CI for the correct full-text/genre
        To search CantusID on CI, use json export: 'http://cantusindex.org/json-cid/<CantusID>'

        Returns:
            list of dicts: a list of suggested chants in key-value pairs
        """

        # only displays the chants that occur most often
        NUM_SUGGESTIONS = 5

        cantus_ids = []
        nocs = []  # number of occurence
        chants_in_source = Chant.objects.filter(source=self.source)
        if not chants_in_source:
            return None
        latest_chant = chants_in_source.latest("date_updated")
        cantus_id = latest_chant.cantus_id
        if cantus_id is None:
            return None
        chants_same_cantus_id = Chant.objects.filter(cantus_id=cantus_id)
        for chant in chants_same_cantus_id:
            next_chant = chant.get_next_chant()
            if next_chant:
                # return the number of occurence in the suggestions (not in the entire db)
                if not next_chant.cantus_id in cantus_ids:
                    # cantus_id can be None (some chants don't have one)
                    if next_chant.cantus_id:
                        # add the new cantus_id to the list, count starts from 1
                        cantus_ids.append(next_chant.cantus_id)
                        nocs.append(1)
                if next_chant.cantus_id in cantus_ids:
                    idx = cantus_ids.index(next_chant.cantus_id)
                    nocs[idx] = nocs[idx] + 1
        # sort the nocs and cantus_ids
        sorted_list = sorted(zip(nocs, cantus_ids), reverse=True)
        cantus_ids_sorted = [y for _, y in sorted_list]
        nocs_sorted = [x for x, _ in sorted_list]

        # return only NUM_SUGGESTIONS top chants
        print(cantus_ids_sorted[:NUM_SUGGESTIONS])
        print(nocs_sorted[:NUM_SUGGESTIONS])
        print("total suggestions: ", len(cantus_ids))

        suggested_chants = cantus_ids_sorted[:NUM_SUGGESTIONS]
        suggested_chants_dicts = []

        for i in range(NUM_SUGGESTIONS):
            try:
                suggested_chant = suggested_chants[i]  # suggested_chant is a CantusID
            except IndexError:
                # if the actual number of suggestions is less than NUM_SUGGESTIONS
                break
            # do a search in CI
            response = requests.get(
                "http://cantusindex.org/json-cid/{}".format(suggested_chant)
            )
            assert response.status_code == 200
            # parse the json export to a dict
            # response.json() # can't use this because of the BOM at the beginning of json export
            chant_dict = json.loads(response.text[1:])[0]
            # add number of occurence to the dict, so that we can display it easily
            chant_dict["noc"] = nocs_sorted[i]
            suggested_chants_dicts.append(chant_dict)
        return suggested_chants_dicts

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["source_link"] = reverse("source-detail", args=[self.source_id])
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
        print("other context done")
        context["suggested_chants"] = self.get_suggested_chants()
        print("suggesions done")
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
            new_incipit = incipit + word + " "
            if len(new_incipit) >= 30:
                break
            incipit = new_incipit
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
    now this is implemented as [send a search request to CI -> scrape the returned html table]
    But, it is possible to use CI json export. 
    To do a text search on CI, use 'http://cantusindex.org/json-text/<text to search>'
    """

    template_name = "ci_search.html"

    def get_context_data(self, **kwargs):
        MAX_PAGE_NUMBER_CI = 5

        context = super().get_context_data(**kwargs)
        search_term = kwargs["search_term"]
        search_term = search_term.replace(" ", "+")  # for multiple keywords
        # Create empty list for the 3 types of info
        cantus_id = []
        genre = []
        full_text = []

        # scrape multiple pages
        pages = range(0, MAX_PAGE_NUMBER_CI)
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
