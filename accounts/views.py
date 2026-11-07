from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import LoginForm, ProfileForm, RegistrationForm


class StoreLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


def _next_url(request, default):
    target = request.POST.get('next') or request.GET.get('next') or ''
    allowed = url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    return target if target and allowed else default


def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile')

    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Welcome to Z-Store. Your account is ready.')
        return redirect(_next_url(request, 'accounts:profile'))
    return render(
        request,
        'accounts/register.html',
        {'form': form, 'next': request.GET.get('next', '')},
    )


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your details were saved.')
        return redirect('accounts:profile')
    return render(
        request,
        'accounts/profile.html',
        {'form': form, 'recent_orders': request.user.orders.all()[:5]},
    )
