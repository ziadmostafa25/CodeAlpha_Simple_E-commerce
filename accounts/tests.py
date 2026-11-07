from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from orders.models import Order

User = get_user_model()

VALID = {
    'username': 'sara',
    'first_name': 'Sara',
    'last_name': 'Ali',
    'email': 'sara@example.com',
    'password1': 'a-Strong-pass-2026',
    'password2': 'a-Strong-pass-2026',
}


class RegistrationTests(TestCase):
    def test_registering_creates_the_account_and_signs_the_user_in(self):
        response = self.client.post(reverse('accounts:register'), VALID)
        self.assertRedirects(response, reverse('accounts:profile'))
        user = User.objects.get(username='sara')
        self.assertEqual(user.email, 'sara@example.com')
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_the_password_is_stored_hashed(self):
        self.client.post(reverse('accounts:register'), VALID)
        user = User.objects.get(username='sara')
        self.assertNotEqual(user.password, VALID['password1'])
        self.assertTrue(user.check_password(VALID['password1']))

    def test_mismatched_passwords_are_rejected(self):
        response = self.client.post(
            reverse('accounts:register'), {**VALID, 'password2': 'something-else-9'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())
        self.assertContains(response, 'Please correct the highlighted fields.')

    def test_weak_passwords_are_rejected(self):
        for weak in ('12345678', 'password', 'short1'):
            with self.subTest(password=weak):
                response = self.client.post(
                    reverse('accounts:register'), {**VALID, 'password1': weak, 'password2': weak}
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(User.objects.exists())

    def test_email_is_required_and_must_be_unique_ignoring_case(self):
        User.objects.create_user('first', 'Sara@Example.com', 'pass-12345')
        response = self.client.post(reverse('accounts:register'), VALID)
        self.assertContains(response, 'An account with this email already exists.')
        response = self.client.post(reverse('accounts:register'), {**VALID, 'email': ''})
        self.assertEqual(User.objects.count(), 1)

    def test_username_must_be_unique(self):
        User.objects.create_user('sara', 'other@example.com', 'pass-12345')
        response = self.client.post(reverse('accounts:register'), VALID)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)

    def test_next_page_is_followed_only_when_safe(self):
        response = self.client.post(
            reverse('accounts:register'), {**VALID, 'next': reverse('orders:checkout')}
        )
        self.assertRedirects(response, reverse('orders:checkout'), fetch_redirect_response=False)
        self.client.logout()
        User.objects.all().delete()
        response = self.client.post(
            reverse('accounts:register'), {**VALID, 'next': 'https://evil.example/'}
        )
        self.assertRedirects(response, reverse('accounts:profile'))

    def test_signed_in_users_are_sent_to_their_account(self):
        self.client.post(reverse('accounts:register'), VALID)
        response = self.client.get(reverse('accounts:register'))
        self.assertRedirects(response, reverse('accounts:profile'))


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('sara', 'sara@example.com', 'a-Strong-pass-2026')

    def test_login_with_the_right_password(self):
        response = self.client.post(
            reverse('accounts:login'), {'username': 'sara', 'password': 'a-Strong-pass-2026'}
        )
        self.assertRedirects(response, reverse('store:home'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_login_with_a_wrong_password_shows_an_error(self):
        response = self.client.post(
            reverse('accounts:login'), {'username': 'sara', 'password': 'wrong'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, 'Please enter a correct username and password')

    def test_login_follows_a_safe_next_page(self):
        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'sara', 'password': 'a-Strong-pass-2026', 'next': reverse('orders:list')},
        )
        self.assertRedirects(response, reverse('orders:list'), fetch_redirect_response=False)

    def test_login_ignores_an_external_next_page(self):
        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'sara', 'password': 'a-Strong-pass-2026', 'next': 'https://evil.example/'},
        )
        self.assertRedirects(response, reverse('store:home'))

    def test_logout_works_with_post(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('store:home'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_refuses_get_requests(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('accounts:logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)


class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'sara', 'sara@example.com', 'a-Strong-pass-2026', first_name='Sara'
        )
        self.other = User.objects.create_user('omar', 'omar@example.com', 'a-Strong-pass-2026')

    def make_order(self, user, reference):
        return Order.objects.create(
            user=user, reference=reference, customer_name='x', phone='01012345678',
            email='x@example.com', governorate='Cairo', address='10 Some Street, Cairo',
            payment_method='cod', subtotal=100, shipping_fee=0, total=100,
        )

    def test_profile_needs_a_signed_in_user(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)

    def test_profile_shows_only_my_orders(self):
        self.make_order(self.user, 'ZS-MINE0001')
        self.make_order(self.other, 'ZS-THEIRS01')
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertContains(response, 'ZS-MINE0001')
        self.assertNotContains(response, 'ZS-THEIRS01')

    def test_details_can_be_updated(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse('accounts:profile'),
            {'first_name': 'Sarah', 'last_name': 'Ali', 'email': 'new@example.com'},
        )
        self.user.refresh_from_db()
        self.assertEqual((self.user.first_name, self.user.email), ('Sarah', 'new@example.com'))

    def test_email_cannot_be_taken_from_another_account(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('accounts:profile'),
            {'first_name': 'Sara', 'last_name': '', 'email': 'OMAR@example.com'},
        )
        self.assertContains(response, 'An account with this email already exists.')
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'sara@example.com')
