from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from .models import cow
from .serializers import CowSerializer

class CowViewSet(viewsets.ModelViewSet):
    queryset = cow.objects.all()
    serializer_class = CowSerializer

def list(self, request):
    queryset = self.get_queryset()
    serializer = CowSerializer(queryset, many=True)
    return Response(serializer.data)

def create(self, request):
    serializer = CowSerializer(data=request.data)
    if serializer.is_valid():
         serializer.save()
         return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)

def retrieve(self, request, pk=None):
    cow = cow.object.get_object(pk=pk)
    serializer = CowSerializer(cow)
    return Response(serializer.data)

def update(self, request, pk=None):
    cow = cow.object.get_object(pk=pk)
    serializer = CowSerializer(cow, data=request.data)
    if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
    return Response(serializer.errors, status=400)

def destroy(self, request, pk=None):
    cow = cow.object.get_object(pk=pk)
    cow.delete()
    return Response(status=204)