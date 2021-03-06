from django.db import models

from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel

# Create your models here.
from wagtail.core.fields import StreamField, RichTextField
from wagtail.core.models import Collection, Page, PageManager
from wagtail.contrib.forms.models import AbstractEmailForm, AbstractFormField
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.search import index
from wagtail.snippets.models import register_snippet
from wagtail.admin.edit_handlers import FieldPanel, StreamFieldPanel
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.models import TaggedItemBase, TagBase, Tag as TaggitTag
from base.blocks import ExtraStreamBlock
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from base.models import HomePage, StandardPage
from django.db.models import Q
from datetime import datetime, timedelta
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

today = datetime.today().date()

class DifusionCulturalHomePage(HomePage):
    def get_nuevos_bisnietos(self):
        return Page.objects.live().public().filter(Q(depth__gte=5)).filter(difusionculturalnoticia__fecha_fin__gte=today)[:6]

    def get_articulos_blog(self):
        return Page.objects.type(DifusionCulturalBlogArticulo).live().public()[:6]

    parent_page_types = ['wagtailcore.Page']

    @classmethod
    def can_create_at(cls, parent):
        # You can only create one of these!
        return super(DifusionCulturalHomePage, cls).can_create_at(parent) \
               and not cls.objects.exists()

    class Meta:
        verbose_name = "Inicio"



@register_snippet
class DifusionCulturalBlogCategoria(ClusterableModel):
    categoria = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True, max_length=80)

    panels = [
        FieldPanel('categoria'),
        FieldPanel('slug'),
    ]

    def __str__(self):
        return self.categoria

    def natural_key(self):
        return self.slug

    class Meta:
        verbose_name = "Categor??a (blog)"
        verbose_name_plural = "Categor??as (blog)"


@register_snippet
class DifusionCulturalBlogArticuloEtiqueta(TaggedItemBase):
    content_object = ParentalKey('DifusionCulturalBlogArticulo', related_name='blog_articulo_tags')


class DifusionCulturalBlogIndex(RoutablePageMixin, Page):
    subpage_types = ['DifusionCulturalBlogArticulo']
    parent_page_types = ['DifusionCulturalHomePage']

    @classmethod
    def can_create_at(cls, parent):
        # You can only create one of these!
        return super(DifusionCulturalBlogIndex, cls).can_create_at(parent) and not cls.objects.exists()

    def get_context(self, request, *args, **kwargs):
        context = super(DifusionCulturalBlogIndex, self).get_context(request, *args, **kwargs)
        all_posts = self.posts
        paginator = Paginator(all_posts, 6)
        page = request.GET.get("p")
        page = page if page else 1

        try:
            posts = paginator.page(page)
        except PageNotAnInteger:
            posts = paginator.page(1)
            page = 1
        except EmptyPage:
            posts = paginator.page(paginator.num_pages)

        if paginator.num_pages > 7:
            paginas = []
            for i in range(int(page)-3, int(page)+4):
                paginas.append(i)
            if paginas[0] < 1:
                inc = abs(paginas[0]) + 1
                for i in range(len(paginas)):
                    paginas[i] = paginas[i] + inc
                paginas.append(0)
            elif paginas[-1] > paginator.num_pages:
                dec = paginas[-1] - paginator.num_pages
                for i in range(len(paginas)):
                    paginas[i] = paginas[i] - dec
                paginas.insert(0, 0)
            else:
                pass
            if paginas[0] > 1:
                paginas.insert(0, 0)
            if paginas[-1] < paginator.num_pages and paginas[-1] > 0:
                paginas.append(0)
            context['paginas'] = paginas

        context['posts'] = posts
        context['difusion_cultural_cartelera'] = self
        return context

    def get_posts(self):
        return DifusionCulturalBlogArticulo.objects.live().public().order_by('-first_published_at')

    @route(r'^etiqueta/(?P<etiqueta>[-\w]+)/$')
    def posts_proximos_etiqueta(self, request, etiqueta, *args, **kwargs):
        self.search_type = 'etiqueta'
        self.search_term = etiqueta
        self.posts = self.get_posts().filter(etiquetas__slug=etiqueta).order_by('-first_published_at')
        return Page.serve(self, request, *args, **kwargs)

    @route(r'^categoria/(?P<categoria>[-\w]+)/$')
    def posts_proximos_categoria(self, request, categoria, *args, **kwargs):
        self.search_type = 'categoria'
        self.search_term = categoria
        self.posts = self.get_posts().filter(categoria__slug=categoria).order_by('-first_published_at')
        return Page.serve(self, request, *args, **kwargs)

    @route(r'^$')
    def next_post_list(self, request, *args, **kwargs):
        self.posts = self.get_posts().order_by('-first_published_at')
        return Page.serve(self, request, *args, **kwargs)


    class Meta:
        verbose_name = "Blog"
        verbose_name_plural = "Blog"


class DifusionCulturalBlogArticulo(StandardPage):
    autor = models.CharField(max_length=250)
    introduccion = RichTextField(max_length=250)
    cuerpo = StreamField(
        ExtraStreamBlock(), verbose_name="Cuerpo", blank=True
    )
    imagen = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text='Imagen de portada'
    )
    galeria = models.ForeignKey(
        Collection,
        limit_choices_to=~models.Q(name__in=['Root']),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Select the image collection for this gallery.'
    )
    categoria = ParentalKey('DifusionCulturalBlogCategoria', on_delete=models.PROTECT, blank=True)
    etiquetas = ClusterTaggableManager(through='DifusionCulturalBlogArticuloEtiqueta', blank=True)

    search_fields = Page.search_fields + [
        index.SearchField('introduccion'),
        index.SearchField('cuerpo'),
    ]

    content_panels = Page.content_panels + [
        FieldPanel('introduccion'),
        FieldPanel('categoria'),
        FieldPanel('autor'),
        StreamFieldPanel('cuerpo'),
        ImageChooserPanel('imagen'),
        FieldPanel('galeria'),
        FieldPanel('etiquetas'),
    ]

    subpage_types = []
    parent_page_types = ['DifusionCulturalBlogIndex']

    class Meta:
        verbose_name = "Art??culo"
        verbose_name_plural = "Art??culos"


class DifusionCulturalNota(Page):
    body = StreamField(
        ExtraStreamBlock(), verbose_name="Home content block", blank=True
    )

    content_panels = Page.content_panels + [
        StreamFieldPanel('body'),
    ]

    subpage_types = ['DifusionCulturalNota']
    parent_page_types = ['DifusionCulturalHomePage', 'DifusionCulturalPagina', 'DifusionCulturalPaginaCategoria','DifusionCulturalNota']

    class Meta:
        verbose_name = "Nota"
        verbose_name_plural = "Notas"


@register_snippet
class DifusionCulturalCarteleraCategoria(ClusterableModel):
    categoria = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True, max_length=80)

    panels = [
        FieldPanel('categoria'),
        FieldPanel('slug'),
    ]

    def __str__(self):
        return self.categoria

    def natural_key(self):
        return self.slug

    class Meta:
        verbose_name = "Categor??a (cartelera)"
        verbose_name_plural = "Categor??as (cartelera)"


class DifusionCulturalCartelera(RoutablePageMixin, Page):
    subpage_types = ['DifusionCulturalDependencia']
    parent_page_types = ['DifusionCulturalHomePage']

    def get_nietos(self):
        return Page.objects.live().descendant_of(self, inclusive=False).not_child_of(self)

    def get_nuevos_nietos(self):
        return Page.objects.live().descendant_of(self, inclusive=False).not_child_of(self)[:2]

    @classmethod
    def can_create_at(cls, parent):
        # You can only create one of these!
        return super(DifusionCulturalCartelera, cls).can_create_at(parent) \
               and not cls.objects.exists()

    def get_context(self, request, *args, **kwargs):
        context = super(DifusionCulturalCartelera, self).get_context(request, *args, **kwargs)
        all_posts = self.posts
        paginator = Paginator(all_posts, 6)
        page = request.GET.get("p")
        page = page if page else 1

        try:
            posts = paginator.page(page)
        except PageNotAnInteger:
            posts = paginator.page(1)
            page = 1
        except EmptyPage:
            posts = paginator.page(paginator.num_pages)

        if paginator.num_pages > 7:
            paginas = []
            for i in range(int(page)-3, int(page)+4):
                paginas.append(i)

            print(posts)
            print(paginator.num_pages)
            print(paginas)
            if paginas[0] < 1:
                inc = abs(paginas[0]) + 1
                for i in range(len(paginas)):
                    paginas[i] = paginas[i] + inc
                paginas.append(0)
            elif paginas[-1] > paginator.num_pages:
                dec = paginas[-1] - paginator.num_pages
                for i in range(len(paginas)):
                    paginas[i] = paginas[i] - dec
                paginas.insert(0, 0)
            else:
                pass
            if paginas[0] > 1:
                paginas.insert(0, 0)
            if paginas[-1] < paginator.num_pages and paginas[-1] > 0:
                paginas.append(0)
            context['paginas'] = paginas

        context['posts'] = posts
        context['difusion_cultural_cartelera'] = self
        return context

    def get_next_posts(self):
        return DifusionCulturalNoticia.objects.filter(fecha_fin__gte=today).live().public().order_by('-fecha_fin')

    def get_prev_posts(self):
        return DifusionCulturalNoticia.objects.filter(fecha_fin__lt=today).live().public().order_by('-fecha_fin')

    @route(r'^etiqueta/(?P<etiqueta>[-\w]+)/$')
    def posts_proximos_etiqueta(self, request, etiqueta, *args, **kwargs):
        self.search_type = 'etiqueta'
        self.search_term = etiqueta
        self.posts = self.get_next_posts().filter(etiquetas__slug=etiqueta).order_by('-fecha_fin')
        return Page.serve(self, request, *args, **kwargs)

    @route(r'^archivado/etiqueta/(?P<etiqueta>[-\w]+)/$')
    def posts_previos_etiqueta(self, request, etiqueta, *args, **kwargs):
        self.search_type = 'etiqueta'
        self.search_term = etiqueta
        self.posts = self.get_prev_posts().filter(etiquetas__slug=etiqueta).order_by('-fecha_fin')
        return Page.serve(self, request, *args, **kwargs)

    @route(r'^categoria/(?P<categoria>[-\w]+)/$')
    def posts_proximos_categoria(self, request, categoria, *args, **kwargs):
        self.search_type = 'categoria'
        self.search_term = categoria
        self.posts = self.get_next_posts().filter(categoria__slug=categoria).order_by('-fecha_fin')
        return Page.serve(self, request, *args, **kwargs)

    @route(r'^archivado/categoria/(?P<categoria>[-\w]+)/$')
    def posts_previos_categoria(self, request, categoria, *args, **kwargs):
        self.search_type = 'categoria'
        self.search_term = categoria
        self.posts = self.get_prev_posts().filter(categoria__slug=categoria).order_by('-fecha_fin')
        return Page.serve(self, request, *args, **kwargs)

    @route(r'^archivado/$')
    def prev_post_list(self, request, *args, **kwargs):
        self.posts = self.get_prev_posts().order_by('-fecha_fin')
        return Page.serve(self, request, *args, **kwargs)

    @route(r'^$')
    def next_post_list(self, request, *args, **kwargs):
        self.posts = self.get_next_posts().order_by('-fecha_fin')
        return Page.serve(self, request, *args, **kwargs)

    class Meta:
        verbose_name = "Cartelera"
        verbose_name_plural = "Carteleras"


class DifusionCulturalDependencia(RoutablePageMixin, Page):
    subpage_types = ['DifusionCulturalNoticia']
    parent_page_types = ['DifusionCulturalCartelera']

    def get_context(self, request, *args, **kwargs):
        context = super(DifusionCulturalDependencia, self).get_context(request, *args, **kwargs)
        all_posts = self.posts
        paginator = Paginator(all_posts, 6)
        page = request.GET.get("p")
        page = page if page else 1

        try:
            posts = paginator.page(page)
        except PageNotAnInteger:
            posts = paginator.page(1)
            page = 1
        except EmptyPage:
            posts = paginator.page(paginator.num_pages)

        if paginator.num_pages > 7:
            paginas = []
            for i in range(int(page)-3, int(page)+4):
                paginas.append(i)

            print(posts)
            print(paginator.num_pages)
            print(paginas)
            if paginas[0] < 1:
                inc = abs(paginas[0]) + 1
                for i in range(len(paginas)):
                    paginas[i] = paginas[i] + inc
                paginas.append(0)
            elif paginas[-1] > paginator.num_pages:
                dec = paginas[-1] - paginator.num_pages
                for i in range(len(paginas)):
                    paginas[i] = paginas[i] - dec
                paginas.insert(0, 0)
            else:
                pass
            if paginas[0] > 1:
                paginas.insert(0, 0)
            if paginas[-1] < paginator.num_pages and paginas[-1] > 0:
                paginas.append(0)
            context['paginas'] = paginas

        context['posts'] = posts
        context['difusion_cultural_cartelera'] = self
        return context

    def get_next_posts(self):
        return DifusionCulturalNoticia.objects.filter(fecha_fin__gte=today).live().public().order_by('-fecha_fin')

    @route(r'^$')
    def next_post_list(self, request, *args, **kwargs):
        self.posts = self.get_next_posts().order_by('-fecha_fin')
        return Page.serve(self, request, *args, **kwargs)

    class Meta:
        verbose_name = "Dependencia"
        verbose_name_plural = "Dependencias"


class DifusionCulturalNoticiaManager(PageManager):
    def ultimos(self):
        return self.order_by('-fecha')


@register_snippet
class DifusionCulturalNoticiaEtiqueta(TaggedItemBase):
    content_object = ParentalKey('DifusionCulturalNoticia', related_name='noticia_tags')


@register_snippet
class Tag(TaggitTag):
    class Meta:
        proxy = True


class DifusionCulturalNoticia(Page):
    fecha_inicio = models.DateField("Fecha inicio", null=True)
    fecha_fin = models.DateField("Fecha fin", null=True)
    hora_inicio = models.TimeField("Hora inicio", null=True)
    hora_fin = models.TimeField("Hora fin", null=True)

    introduccion = RichTextField(max_length=250)
    ubicacion = RichTextField(max_length=250, blank=True)
    consideraciones = RichTextField(max_length=250, blank=True, null=True)

    cuerpo = StreamField(
        ExtraStreamBlock(), verbose_name="Page body", blank=True
    )
    imagen = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text='Imagen de portada'
    )
    galeria = models.ForeignKey(
        Collection,
        limit_choices_to=~models.Q(name__in=['Root']),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Select the image collection for this gallery.'
    )
    categoria = ParentalKey('DifusionCulturalCarteleraCategoria', on_delete=models.PROTECT, blank=True)
    etiquetas = ClusterTaggableManager(through='DifusionCulturalNoticiaEtiqueta', blank=True)

    search_fields = Page.search_fields + [
        index.SearchField('introduccion'),
        index.SearchField('cuerpo'),
    ]

    content_panels = Page.content_panels + [
        FieldPanel('fecha_inicio'),
        FieldPanel('fecha_fin'),
        FieldPanel('hora_inicio'),
        FieldPanel('hora_fin'),
        FieldPanel('introduccion'),
        FieldPanel('ubicacion'),
        FieldPanel('consideraciones'),
        StreamFieldPanel('cuerpo'),
        ImageChooserPanel('imagen'),
        FieldPanel('galeria'),
        FieldPanel('categoria'),
        FieldPanel('etiquetas'),
    ]

    objects = DifusionCulturalNoticiaManager()

    subpage_types = []
    parent_page_types = ['DifusionCulturalDependencia']

    @property
    def esta_vigente(self):
        return self.fecha_fin > (today - timedelta(days=1))

    @property
    def difusion_cultural_cartelera(self):
        return self.get_parent().specific.get_parent().specific

    @property
    def difusion_cultural_cartelera_slug(self):
        return self.get_parent().specific.get_parent().specific.slug


    def get_context(self, request, *args, **kwargs):
        context = super(DifusionCulturalNoticia, self).get_context(request, *args, **kwargs)
        context['difusion_cultural_cartelera'] = self.difusion_cultural_cartelera
        return context

    class Meta:
        verbose_name = "Noticia"
        verbose_name_plural = "Noticias"


class DifusionCulturalPaginaCategoria(Page):
    subpage_types = ['DifusionCulturalPagina', 'DifusionCulturalNota']
    parent_page_types = ['DifusionCulturalHomePage']

    class Meta:
        verbose_name = "Categor??a de p??gina"
        verbose_name_plural = "Categor??as de p??gina"


class DifusionCulturalPagina(Page):
    introduccion = models.CharField(max_length=250)
    cuerpo = StreamField(
        ExtraStreamBlock(), verbose_name="Page body", blank=True
    )
    imagen = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text='Imagen de portada'
    )
    galeria = models.ForeignKey(
        Collection,
        limit_choices_to=~models.Q(name__in=['Root']),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Select the image collection for this gallery.'
    )

    search_fields = Page.search_fields + [
        index.SearchField('introduccion'),
        index.SearchField('cuerpo'),
    ]

    content_panels = Page.content_panels + [
        FieldPanel('introduccion'),
        StreamFieldPanel('cuerpo'),
        ImageChooserPanel('imagen'),
        FieldPanel('galeria'),

    ]

    subpage_types = ['DifusionCulturalPagina', 'DifusionCulturalNota']
    parent_page_types = ['DifusionCulturalPagina', 'DifusionCulturalPaginaCategoria', 'DifusionCulturalHomePage']


    class Meta:
        verbose_name = "P??gina"
        verbose_name_plural = "p??ginas"
