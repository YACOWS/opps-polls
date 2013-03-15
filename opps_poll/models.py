# -*- coding: utf-8 -*-
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from tagging.fields import TagField

from opps.core.models import Publishable
from opps.channel.models import Channel
from opps.article.models import Post
from opps.image.models import Image

from opps_poll.forms import MultipleChoiceForm, SingleChoiceForm


class Poll(Publishable):

    question = models.CharField(_(u"Question"), max_length=255)
    multiple_choices = models.BooleanField(_(u"Allow multiple choices"),
        default=False)
    display_choice_images = models.BooleanField(_(u"Display Choice images"),
        default=True)

    slug = models.SlugField(_(u"URL"), max_length=150, unique=True,
                            db_index=True)

    headline = models.TextField(_(u"Headline"), blank=True)

    channel = models.ForeignKey(Channel, null=True, blank=True,
                                on_delete=models.SET_NULL)
    posts = models.ManyToManyField(Post, null=True, blank=True,
                                   related_name='poll_post',
                                   through='PollPost')

    main_image = models.ForeignKey(Image,
                                   verbose_name=_(u'Poll Image'), blank=True,
                                   null=True, on_delete=models.SET_NULL,
                                   related_name='poll_image')

    tags = TagField(null=True, verbose_name=_(u"Tags"))
    date_end = models.DateTimeField(_(u"End date"), null=True, blank=True)
    position  = models.IntegerField(_(u"Position"), default=0)
    template_path  = models.CharField(_(u"Template Path"), blank=True,
                                     null=True, max_length=255)


    @property
    def is_opened(self):
        if not self.date_end:
            return True
        return self.date_end >= timezone.now()

    @property
    def choices(self):
        return self.choice_set.all()

    def form(self, *args, **kwargs):
        if self.multiple_choices:
            return MultipleChoiceForm(self.choices, self.display_choice_images, *args, **kwargs)
        else:
            return SingleChoiceForm(self.choices, self.display_choice_images, *args, **kwargs)

    def vote(self, request):
        try:
            choice_ids = request.POST.getlist('choices')
        except:
            choices_ids = (request.POST.get('choices'),)

        choices = [Choice.objects.get(pk=int(choice_id)) for choice_id in choice_ids]

        for choice in choices:
            choice.vote()
            choice.save()

        return choices

    def __unicode__(self):
        return self.question

    class Meta:
        ordering = ['position']


class PollPost(models.Model):
    post = models.ForeignKey(Post, verbose_name=_(u'Poll Post'), null=True,
                             blank=True, related_name='pollpost_post',
                             on_delete=models.SET_NULL)
    poll = models.ForeignKey(Poll, verbose_name=_(u'Poll'), null=True,
                                   blank=True, related_name='poll',
                                   on_delete=models.SET_NULL)


    def __unicode__(self):
        return "{0}-{1}".format(self.poll.slug, self.post.slug)


class Choice(models.Model):

    poll = models.ForeignKey(Poll)
    choice = models.CharField(max_length=255, null=False, blank=False)
    votes = models.IntegerField(null=True, blank=True, default=0)
    image = models.ForeignKey(Image,
                            verbose_name=_(u'Choice Image'), blank=True,
                            null=True, on_delete=models.SET_NULL,
                            related_name='choice_image')
    position  = models.IntegerField(_(u"Position"), default=0)

    def __unicode__(self):
        return self.choice

    def vote(self):
        self.votes += 1

    class Meta:
        ordering = ['position']
