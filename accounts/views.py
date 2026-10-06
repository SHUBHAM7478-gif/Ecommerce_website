from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import (
    RegisterForm,
    LoginForm,
    UserUpdateForm,
    ProfileUpdateForm,
)



# Register 

@require_http_methods(['GET', 'POST'])
def register(request):

    if request.user.is_authenticated:
        messages.info(request, "You are already logged in.")
        return redirect('store:home')


    form = RegisterForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(
            request, 
            f'Welcome, {user.username}! Your account was created. please log in.'
            )
        return redirect('accounts:login')

    return render(request, 'accounts/register.html', {'form': form})



# LOGIN

@require_http_methods(["GET", "POST"])
def login_view(request):

    if request.user.is_authenticated:
        return redirect('store:home')

    form = LoginForm(request.POST or None)
    error = None

    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username'].strip()
        password = form.cleaned_data['password']

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                error="This account has been disabled"
            else:
                login(request, user)

                if not form.cleaned_data.get('remember_me'):
                    request.session.set_expiry(0)

                messages.success(request, f'Welcome back, {user.username}!')

                next_url = (
                    request.POST.get('next')
                    or request.GET.get('next')
                    or reverse('store:home')
                    )
                    
                return redirect(next_url)

        else:
            error = 'Invalid username or password.'

    return render(request, 'accounts/login.html', {
        'form':form,
        'error':error
    })





#  LOGOUT

@require_http_methods(['GET', 'POST'])
def logout_view(request):

    if request.method == 'POST':
        logout(request)
        messages.info(request, "you have been logged out.")
        return redirect('store:home')
    
    # user must be authenticated to see the confirm page
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    return render(request, 'accounts/logout.html')


# PROFILE

def profile(request):

    if not hasattr(request.user, 'profile'):
        from .models import Profile
        Profile.objects.create(user=request.user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(
            request.POST,
            request.FILES,          # avatar upload
            instance=request.user.profile,
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile was updated successfully.")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    return render(request, 'accounts/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })



# DELETE ACCOUNT
@login_required
def delete_account(request):
    username = request.user.username
    user = request.user
    logout(request)
    user.delete()
    messages.success(request, f"Account'{username}' has been deleted.")
    return redirect('store:home')