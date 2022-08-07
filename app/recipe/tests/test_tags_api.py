"""
Test for tags API
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from recipe.serializers import TagSerializer

from core.models import Tag, Recipe

TAGS_URL = reverse("recipe:tag-list")


def detail_url(tag_id):
    """Create and return a detail tag url."""
    return reverse('recipe:tag-detail', args=[tag_id])


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
        """List of tags is limited to user's tags."""
        other_user = create_user("user2@example.com", 'testpass123')
        tag = create_tag(self.user, name="Italian")
        create_tag(other_user, name="Greek")

        res = self.client.get(TAGS_URL)

        Tag.objects.all().order_by('-name')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)

    def test_partial_update(self):
        """Update a tag."""
        tag = create_tag(self.user, name="Fish")

        payload = {
            'name': 'Lobster'
        }

        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()

        self.assertEqual(tag.name, payload['name'])
        self.assertEqual(tag.user, self.user)

    def test_delete_tag(self):
        """Delete a tag."""
        tag = create_tag(self.user, name="Stews")

        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tag.objects.filter(id=tag.id).exists())

    def test_filter_tagss_assigned_to_recipes(self):
        """Test restricting ingredients to those assigned to recipes."""
        tag1 = Tag.objects.create(user=self.user, name="Dinner")
        tag2 = Tag.objects.create(user=self.user, name="Lunch")

        recipe = Recipe.objects.create(
            title='Stir Fry',
            cost=Decimal(6.2),
            time_minutes=10,
            user=self.user
        )
        recipe.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})
        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        """Test filtered ingredients returns a unique list."""
        tag1 = Tag.objects.create(user=self.user, name="Breakfast")
        r1 = Recipe.objects.create(
            title="Ham and Eggs",
            cost=Decimal(5.1),
            time_minutes=5,
            user=self.user
        )
        r1.tags.add(tag1)
        r2 = Recipe.objects.create(
            title="Eggs Florentine",
            cost=Decimal(10.9),
            time_minutes=15,
            user=self.user
        )
        r2.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
