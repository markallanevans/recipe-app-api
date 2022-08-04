"""
Test for tags API
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from recipe.serializers import TagSerializer

from core.models import Tag

TAGS_URL = reverse("recipe:tag-list")


def create_user(email='email@example.com', password='testpass123'):
    """Create and return a user"""
    user = get_user_model().objects.create(email=email, password=password)

    return user


def create_tag(user, name):
    """Create and return a tag"""
    tag = Tag.objects.create(user=user, name=name)

    return tag


class PublicTagsApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """Test authenticated API requests"""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """ Test retrieving list of tags. """
        create_tag(self.user, name="Italian")
        create_tag(self.user, name="Greek")

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """ List of tags is limited to user's tags."""
        other_user = create_user("user2@example.com", 'testpass123')
        tag = create_tag(self.user, name="Italian")
        create_tag(other_user, name="Greek")

        res = self.client.get(TAGS_URL)

        Tag.objects.all().order_by('-name')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)
