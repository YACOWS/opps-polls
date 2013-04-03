# -*- coding: utf-8 -*-
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from taggit.managers import TaggableManager

from opps.core.models import Publishable, BaseBox, BaseConfig

from .forms import MultipleChoiceForm, SingleChoiceForm


class Poll(Publishable):

    question = models.CharField(_(u"Question"), max_length=255)
    multiple_choices = models.BooleanField(_(u"Allow multiple choices"),
        default=False)
    max_multiple_choices = models.PositiveIntegerField(
                                    _(u"Max number of selected choices"),
                                    blank=True, null=True)
    min_multiple_choices = models.PositiveIntegerField(
                                    _(u"Min number of selected choices"),
                                    blank=True, null=True)
    display_choice_images = models.BooleanField(_(u"Display Choice images"),
        default=False)

    slug = models.SlugField(_(u"URL"), max_length=150, unique=True,
                            db_index=True)

    headline = models.TextField(_(u"Headline"), blank=True)

    channel = models.ForeignKey('channels.Channel', null=True, blank=True,
                                on_delete=models.SET_NULL)
    posts = models.ManyToManyField('articles.Post', null=True, blank=True,
                                   related_name='poll_post',
                                   through='PollPost')

    main_image = models.ForeignKey('images.Image',
                                   verbose_name=_(u'Poll Image'), blank=True,
                                   null=True, on_delete=models.SET_NULL,
                                   related_name='poll_image')

    tags = TaggableManager(blank=True)
    date_end = models.DateTimeField(_(u"End date"), null=True, blank=True)
    position  = models.IntegerField(_(u"Position"), default=0)
    show_results = models.BooleanField(_(u"Show results page"), default=True)


    @property
    def is_opened(self):
        now = timezone.now()
        self.date_available = self.date_available or now
        if not self.date_end and self.date_available <= now:
            return True
        elif not self.date_end and self.date_available > now:
            return False
        return now >= self.date_available and now <= self.date_end

    @property
    def choices(self):
        return self.choice_set.all()

    @property
    def cookie_name(self):
        return "opps_poll_{0}".format(self.pk)

    @property
    def vote_count(self):
        return self.choices.aggregate(Sum('votes'))['votes__sum']

    def get_voted_choices(self, choices):
        """
        receives a str separated by "|"
        returns a list of choices
        """
        choices_ids = [int(choice_id) for choice_id in choices.split("|")]
        return self.choice_set.filter(id__in=choices_ids)

    def form(self, *args, **kwargs):
        if self.multiple_choices:
            return MultipleChoiceForm(self.choices, self.display_choice_images, *args, **kwargs)
        else:
            return SingleChoiceForm(self.choices, self.display_choice_images, *args, **kwargs)

    def vote(self, request):
        try:
            choices_ids = request.POST.getlist('choices')
        except:
            choices_ids = (request.POST.get('choices'),)

        choices = self.choice_set.filter(id__in=choices_ids)

        for choice in choices:
            choice.vote()
            choice.save()

        return choices

    def __unicode__(self):
        return self.question

    class Meta:
        ordering = ['position']


class PollPost(models.Model):
    post = models.ForeignKey('articles.Post', verbose_name=_(u'Poll Post'), null=True,
                             blank=True, related_name='pollpost_post',
                             on_delete=models.SET_NULL)
    poll = models.ForeignKey('polls.Poll', verbose_name=_(u'Poll'), null=True,
                                   blank=True, related_name='poll',
                                   on_delete=models.SET_NULL)


    def __unicode__(self):
        return u"{0}-{1}".format(self.poll.slug, self.post.slug)


class Choice(models.Model):

    poll = models.ForeignKey('polls.Poll')
    choice = models.CharField(max_length=255, null=False, blank=False)
    votes = models.IntegerField(null=True, blank=True, default=0)
    image = models.ForeignKey('images.Image',
                            verbose_name=_(u'Choice Image'), blank=True,
                            null=True, on_delete=models.SET_NULL,
                            related_name='choice_image')
    position  = models.IntegerField(_(u"Position"), default=0)

    def __unicode__(self):
        return self.choice

    def vote(self):
        self.votes += 1

    @property
    def percentage(self):
        return float(self.votes) / float(self.poll.vote_count) * 100

    class Meta:
        ordering = ['position']


class PollBox(BaseBox):

    polls = models.ManyToManyField(
        'polls.Poll',
        null=True, blank=True,
        related_name='pollbox_polls',
        through='polls.PollBoxPolls'
    )


class PollBoxPolls(models.Model):
    pollbox = models.ForeignKey(
        'polls.PollBox',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='pollboxpolls_pollboxes',
        verbose_name=_(u'Poll Box'),
    )
    poll = models.ForeignKey(
        'polls.Poll',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='pollboxpolls_polls',
        verbose_name=_(u'Poll'),
    )
    order = models.PositiveIntegerField(_(u'Order'), default=0)

    def __unicode__(self):
        return u"{0}-{1}".format(self.pollbox.slug, self.poll.slug)

    def clean(self):

        if not self.poll.published:
            raise ValidationError('Poll not published!')

        if self.poll.date_available <= timezone.now():
            raise ValidationError('Poll not published!')


class PollConfig(BaseConfig):

    poll = models.ForeignKey(
        'polls.Poll',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='pollconfig_polls',
        verbose_name=_(u'Poll'),
    )

    class Meta:
        permissions = (("developer", "Developer"),)
        unique_together = ("key_group", "key", "site", "channel", "article", "poll")

