from django.shortcuts import render

from awl.utils import render_page

def embed(request):
    return render_page(request, 'embed.html')
