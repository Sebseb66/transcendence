import os, json
from urllib.parse import urlencode
from dotenv import load_dotenv
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
from .models import FriendList, FriendRequest
from .utils import Oauth42, get_friend_request_or_false
from .friend_request_status import FriendRequestStatus
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, HttpResponseBadRequest
from django.urls import reverse
from django.template.loader import render_to_string
from render_block import render_block_to_string
from django.middleware.csrf import get_token
from game.models import LeaderboardEntry
#fred
from dataclasses import dataclass
from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_POST
from faker import Faker
from django_htmx.middleware import HtmxDetails
from django.core.paginator import Paginator
from django_htmx.http import HttpResponseClientRedirect,push_url

# Typing pattern recommended by django-stubs:
# https://github.com/typeddjango/django-stubs#how-can-i-create-a-httprequest-thats-guaranteed-to-have-an-authenticated-user
class HtmxHttpRequest(HttpRequest):
    htmx: HtmxDetails
    
import logging
# logger = logging.getLogger(__name__)
logger = logging.getLogger("users")
#fred

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = 'https://localhost/users/callback/'

# Define the FROMLOGIN and FROMSIGNUP variables
FROMLOGIN = 'd56b699830e77ba53855679cb1d252da'
FROMSIGNUP = '7d2abf2d0fa7c3a0c13236910f30bc43'

def build_authorize_uri(state_value):
    logger.debug("== build_authorize_uri")
    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': 'public',
        'state': state_value
    }
    return f"https://api.intra.42.fr/oauth/authorize?{urlencode(params)}"

# Update your views to use the new build_authorize_uri function
@require_http_methods(['GET', 'POST'])
def signup_v(request: HtmxHttpRequest) -> HttpResponse:
    logger.debug("== signup_v")
    context = {
        'authorize_uri': build_authorize_uri(FROMSIGNUP),
        'show_alerts': True,
        'request': request
    }
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your account has been created! You are now able to log in.')
            context['form'] = AuthenticationForm()
            return render(request, 'users/login.html', context)
    else:
        form = UserRegisterForm()
    context['form'] = form

    return push_url(render(request, 'users/signup.html', context),'')

@require_http_methods(['GET', 'POST'])
def login_v(request: HtmxHttpRequest) -> HttpResponse:
    logger.debug("== login_v")
    template_name = "home/welcome.html"
    # if request.htmx:
    #     template_name += "#my_htmx_content"
    context = {
        'authorize_uri': build_authorize_uri(FROMLOGIN),
        'show_alerts': True,
        'request': request
    }
    if request.user and request.user.is_authenticated:
        logger.debug("== login_v : déjà identifié => home")
        return push_url(render(request, template_name, context),'')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            user.profile.active = True
            login(request, user)
            context['request'] = request
            logger.debug("== login_v : identification ok")
            return push_url(render(request, template_name, context),'')
            # return render(request, 'home/welcome.html', context)
    else:
        form = AuthenticationForm()
    context['form'] = form
    template_name = "users/login.html"
    # if request.htmx:
    #     template_name += "#my_htmx_content"
    return push_url(render(request, template_name, context),'')
    # return render(request, 'users/login.html', context)



"""
Callback for Oauth2 logic
--
catches tmp_code, exchanges it for an access token, use that
token to get user informations
"""
@require_GET
def callback(request: HtmxHttpRequest) -> None:
    logger.debug("== callback")
    page_origin = request.GET.get('state')
    authorization_code = request.GET.get('code')
    if authorization_code is None:
        return HttpResponseBadRequest("Bad Request: Missing 'code' parameter")
    
    # exchange authorization code for access token
    o42 = Oauth42()
    token = o42.get_token(authorization_code)
    if token == None:
        messages.warning(request, f"Couldn't exchange code for access token.")
        return redirect('users:signup')

    # use token to request user data
    user_data = o42.get_user_data(token)
    if user_data == None:
        messages.warning(request, f'Error: Unable to login. Try signing-up. Probably 401 "Unauthorized"')
        return redirect('users:signup')
    username_42 = user_data.get('login')
    email_42 = user_data.get('email')

    # when user is in database
    if username_42 in str(User.objects.all()):
        known_user = User.objects.get(username=username_42)
        if known_user.profile.isstudent:
            known_user.profile.active = True
            login(request, known_user)
            if 'next' in request.POST:
                return redirect(request.POST.get('next'))
            else:
                return redirect('home:welcome')
        else:
            if page_origin == FROMLOGIN:
                messages.warning(request, "The account you're trying to connect to was created without 42intra. Please enter your credentials to log in.")
                return redirect('users:login')
            else:
                messages.warning(request, f'The username <strong>{username_42}</strong> already exists. Pleaser enter another one.')
                return redirect('users:signup')
    # when user is NOT in database
    if page_origin == FROMLOGIN:
        messages.info(request, "No corresponding account was found. Please sign-up first.")
        return redirect('users:signup')
    elif page_origin == FROMSIGNUP:
        newUser = User.objects.create_user(username_42, email_42)
        newUser.profile.isstudent = True
        newUser.profile.save()
        messages.success(request, f'Your account has been created! You are now able to log in.')
        return redirect('users:login')

@require_POST
def logout_v(request: HtmxHttpRequest) -> None:
    logger.debug("== logout_v")
    if request.method == 'POST':
        user = request.user
        user.profile.active = False
        user.profile.save()
        logout(request)
        messages.info(request, f'You have been logged out.')
        return redirect('users:login')

################################################################################

"""
Profile view of current user or another one
"""
@login_required(login_url='/users/login/?redirected=true')
def profile(request: HtmxHttpRequest, username: str) -> HttpResponse:
    logger.debug("== profile")
    context = {}
    try:
        displayed_user = User.objects.get(username=username)
    except:
        return render(request, '404.html', {
            'message': 'User not found',
            "show_alerts": True
        })
    if displayed_user:
        context['displayed_user'] = displayed_user
        context['username'] = displayed_user.username
        context['id'] = displayed_user.id
        context['email'] = displayed_user.email
        context['profile_img'] = displayed_user.profile.image.url
        context['wins'] = displayed_user.profile.wins
        context['losses'] = displayed_user.profile.losses
        context['active'] = displayed_user.profile.active
        context['description'] = displayed_user.profile.description
        context['all_users'] = User.objects.all()
        context['blocklist'] = displayed_user.profile.blocklist.all()

        try:
            friend_list = FriendList.objects.get(user=displayed_user)
        except FriendList.DoesNotExist:
            friend_list = FriendList(user=displayed_user)
            friend_list.save()
        friends = friend_list.friends.all()
        context['friends'] = friends

        # Fetch the latest matches for the displayed user
        latest_matches = LeaderboardEntry.objects.filter(user=displayed_user).order_by('-timestamp')[:10]
        context['latest_matches'] = latest_matches

        # Define template variables
        is_self = True
        is_friend = False
        request_sent = FriendRequestStatus.NO_REQUEST_SENT.value
        friend_requests = None
        user = request.user
        # Logged in but NOT looking at your own profile
        if user.is_authenticated and user != displayed_user:
            is_self = False
            if friends.filter(pk=user.id):
                is_friend = True
            else:
                is_friend = False
                # CASE1: Request has been sent from THEM to YOU: THEM_TO_YOU
                if get_friend_request_or_false(sender=displayed_user, receiver=user) != False:
                    request_sent = FriendRequestStatus.THEM_SENT_TO_YOU.value
                    context['pending_friend_request_id'] = get_friend_request_or_false(
                        sender=displayed_user,
                        receiver=user
                    ).id
                # CASE2: Request has been sent from YOU to THEM: YOU_SENT_TO_THEM
                elif get_friend_request_or_false(sender=user, receiver=displayed_user) != False:
                    request_sent = FriendRequestStatus.YOU_SENT_TO_THEM.value
                # CASE3: No request has been sent: NO_REQUEST_SENT
                else:
                    request_sent = FriendRequestStatus.NO_REQUEST_SENT.value
        # NOT logged in
        elif not user.is_authenticated:
            is_self = False
        # Logged in and looking at your profile
        else:
            try:
                friend_requests = FriendRequest.objects.filter(receiver=user, is_active=True)
            except:
                pass
        
        context["is_self"] = is_self
        context["is_friend"] = is_friend
        context['request_sent'] = request_sent
        context['friend_requests'] = friend_requests

    context['show_alerts'] = True

    if 'HTTP_HX_REQUEST' in request.META:
        if request.GET.get('fromEdit', 'False') == 'True':
            return render(request, 'users/profile.html', context)
        context['request'] = request
        context['my_csrf'] = get_token(request)
        b_body = render_block_to_string('users/profile.html', 'body', context)
        b_script = render_block_to_string('users/profile.html', 'script_body', context)
        return push_url(HttpResponse(b_body + b_script),'')

    return push_url(render(request, 'users/profile.html', context),'')

"""
Logic for deleting a user > profile > friendlist
"""
@login_required(login_url='/users/login/?redirected=true')
def deleteprofile(request: HtmxHttpRequest, username: str) -> None:
    logger.debug("== deleteprofile")
    # Ensure the user is deleting their own profile or is a superuser
    if request.user.username != username and not request.user.is_superuser:
        return push_url(render(request, '404.html'),'')

    # Retrieve the user instance
    try:
        user_to_delete = User.objects.get(username=username)
    except User.DoesNotExist:
        return push_url(render(request, '500.html', {'message': 'User not found'}),'')
    
    # Delete the user instance
    user_to_delete.delete()
    return redirect('users:login')

"""
Settings page for editing user info
"""
@login_required(login_url='/users/login/?redirected=true')
def editprofile(request: HtmxHttpRequest) -> HttpResponse:
    logger.debug("== editprofile")
    context = {
        'request': request,
    }
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your account has been updated!')
            context['username'] = request.user.username

            base_url = reverse('users:profile', kwargs={'username': request.user.username})
            return redirect(f'{base_url}?fromEdit=True')
        messages.warning(request, 'NOT VALID')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
    context['u_form'] = u_form
    context['p_form'] = p_form
    if 'HTTP_HX_REQUEST' in request.META:
        context['request'] = request
        b_body = render_block_to_string('users/editprofile.html', 'body', context)
        return push_url(HttpResponse(b_body),'')
    return push_url(render(request, 'users/editprofile.html', context),'')

""""
Friend Request System
"""
def send_friend_request(request: HtmxHttpRequest) -> HttpResponse:
    logger.debug("== send_friend_request")
    user = request.user
    payload = {}
    if request.method == 'POST' and user.is_authenticated:
        user_id = request.POST.get('receiver_user_id')
        if user_id:
            receiver = User.objects.get(pk=user_id)
            try:
                # Get any friend requests (active and not-active)
                friend_requests = FriendRequest.objects.filter(
                    sender=user,
                    receiver=receiver
                )
                # find if any of them are active
                try:
                    for request in friend_requests:
                        if request.is_active:
                            raise Exception("You already sent them a friend request.")
                    # if none are active, then create a new friend request
                    friend_request = FriendRequest(sender=user, receiver=receiver)
                    friend_request.save()
                    payload['response'] = "Friend request sent."
                except Exception as e:
                    payload['response'] = str(e)
            except FriendRequest.DoesNotExist:
                # There are no friend requests so create one
                friend_request = FriendRequest(sender=user, receiver=receiver)
                friend_request.save()
                payload['response'] = "Friend request sent."

            if payload['response'] == None:
                payload['response'] = "Something went wrong."
        else:
            payload['response'] = "Unable to send a friend request."
    else:
        payload['response'] = "You must be authenticated to send a friend request."
    return push_url(HttpResponse(json.dumps(payload), content_type="application/json"),'')

def accept_friend_request(request: HtmxHttpRequest, *args, **kwargs) -> HttpResponse:
    logger.debug("== accept_friend_request")
    user = request.user
    payload = {}
    if request.method == "GET" and user.is_authenticated:
        friend_request_id = kwargs.get("friend_request_id")
        if friend_request_id:
            friend_request = FriendRequest.objects.get(pk=friend_request_id)
            # confirm that it is addressed to logged in user
            if friend_request.receiver == user:
                if friend_request:
                    # found the request. Now accept it
                    friend_request.accept()
                    payload['response'] = 'Friend request accepted'
                else:
                    payload['response'] = 'Something went wrong'
            else:
                payload['response'] = 'That is not your request to accept'
        else:
            payload['response'] = 'Unable to accept that friend request'
    else:
        payload['response'] = 'You must be authenticated to accept a friend request'
    return push_url(HttpResponse(json.dumps(payload), content_type="application/json"),'')

def decline_friend_request(request: HtmxHttpRequest, *args, **kwargs) -> HttpResponse:
    logger.debug("== decline_friend_request")
    user = request.user
    payload = {}
    if request.method == "GET" and user.is_authenticated:
        friend_request_id = kwargs.get("friend_request_id")
        if friend_request_id:
            friend_request = FriendRequest.objects.get(pk=friend_request_id)
            # confirm that it is addressed to logged in user
            if friend_request.receiver == user:
                if friend_request:
                    # foudn the request. Now decline it
                    friend_request.decline()
                    payload['response'] = "Friend request declined"
                else:
                    payload['response'] = "Somethind went wrong"
            else:
                payload['response'] = "That is not your request to decline"
        else:
            payload['response'] = "Unable to decline that friend request"
    else:
        payload['response'] = "You must be authenticated to decline a friend request"
    return push_url(HttpResponse(json.dumps(payload), content_type="application/json"),'')

def cancel_friend_request(request: HtmxHttpRequest) -> HttpResponse:
    logger.debug("== cancel_friend_request")
    user = request.user
    payload = {}
    if request.method == "POST" and user.is_authenticated:
        user_id = request.POST.get("receiver_user_id")
        if user_id:
            receiver = User.objects.get(pk=user_id)
            try:
                friend_requests = FriendRequest.objects.filter(sender=user, receiver=receiver, is_active=True)

            except Exception as e:
                payload['response'] = "Nothing to cancel. Friend request does not exist"
            # There should only every be a single active friend request at any given time.
            # Cancel them all just in case.
            if len(friend_requests) > 1:
                for req in friend_requests:
                    request.cancel()
                payload['response'] = "Friend request cancelled"
            else:
                # found the request. Now cancel it
                friend_requests.first().cancel()
                payload['response'] = "Friend request cancelled"
        else:
            payload['response'] = "Unable to cancel that friend request"
    else:
            payload['response'] = "You must be authenticated to cancel a friend requests"
    return push_url(HttpResponse(json.dumps(payload), content_type="application/json"),'')

def remove_friend(request: HtmxHttpRequest) -> HttpResponse:
    logger.debug("== remove_friend")
    user = request.user
    payload = {}
    if request.method == "POST" and user.is_authenticated:
        user_id = request.POST.get("receiver_user_id")
        if user_id:
            try:
                removee = User.objects.get(pk=user_id)
                friend_list = FriendList.objects.get(user=user)
                friend_list.unfriend(removee)
                payload['response'] = "Successfully removed that friend"
            except Exception as e:
                payload['response'] = f"Something went wrong: {str(e)}"
        else:
            payload['response'] = "There was an error. Unable to remove that friend"
    else:
        payload['response'] = "You must be authenticated to remove a friend"
    return push_url(HttpResponse(json.dumps(payload), content_type="application/json"),'')

def blocking(request: HtmxHttpRequest) -> HttpResponse:
    logger.debug("== blocking")
    current_user = request.user
    blocklist = current_user.profile.blocklist
    action = request.GET.get("action") or request.POST.get("action")
    payload = {}

    if current_user.is_authenticated:
        if request.method == "POST":
            try:
                data = json.loads(request.body)
                user_id = data.get("user_id")  # Assurez-vous de récupérer le user_id correctement du body
                action = data.get("action")
            except json.JSONDecodeError:
                user_id = None
        else:
            user_id = request.GET.get("user_id")
        if user_id:
            target_user = User.objects.get(pk=user_id)

            # add/remove from blocklist
            if action == "block" and target_user not in blocklist.all():
                blocklist.add(target_user)
                if user_id:
                    try:
                        friend_list = FriendList.objects.get(user=current_user)
                        friend_list.unfriend(target_user)
                        payload['response'] = "Successfully removed that friend"
                    except Exception as e:
                        payload['response'] = f"Something went wrong: {str(e)}"
            elif action == "unblock" and target_user in blocklist.all():
                blocklist.remove(target_user)
                payload['response'] = f'unblocked user: {target_user.username}'
            else:
                payload['response'] = 'No user to block or unblock'
        else:
            payload['response'] = 'No user ID in the request'
    else:
        payload['response'] = 'User is not authenticated'
    return push_url(HttpResponse(json.dumps(payload), content_type="application/json"),'')