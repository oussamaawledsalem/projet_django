from implicit.als import AlternatingLeastSquares
from scipy.sparse import coo_matrix
from apps.book.models import Book, User
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import UserInteraction
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
import numpy as np
from django.contrib.auth import get_user_model
from collections import defaultdict

User = get_user_model()

def train_als_model():
    user_book_data = []
    for user in User.objects.all():
        for book in user.favorite_books.all():
            user_book_data.append((user.id, book.id, 1))

    # REMPLACEMENT PANDAS : Créer des listes séparées pour la matrice sparse
    book_ids = [item[1] for item in user_book_data]
    user_ids = [item[0] for item in user_book_data]
    interactions = [item[2] for item in user_book_data]

    # Créer la matrice sparse directement
    sparse_matrix = coo_matrix(
        (interactions, (book_ids, user_ids))
    )

    model = AlternatingLeastSquares(factors=20, regularization=0.1, iterations=20)
    model.fit(sparse_matrix)

    return model, sparse_matrix

@login_required
def recommended_books(request):
    user = request.user
    interactions = UserInteraction.objects.filter(user=user)

    genre_scores = {}
    for interaction in interactions:
        points = 0
        if interaction.viewed:
            points += 1
        if interaction.added_to_cart:
            points += 2
        if interaction.favorited:
            points += 3
        genre = interaction.book.genre
        genre_scores[genre] = genre_scores.get(genre, 0) + points

    favorite_genres = sorted(genre_scores, key=genre_scores.get, reverse=True)

    recommended_books = Book.objects.filter(
        genre__in=favorite_genres
    ).exclude(
        userinteraction__user=user
    ).distinct()[:10]

    context = {
        "recommended_books": recommended_books,
        "favorite_genres": favorite_genres,
    }
    return render(request, "booksRecommendation/recommended_books.html", context)

def get_book_recommendations(book_id, top_n=5):
    # Récupérer tous les livres depuis la base
    books = Book.objects.all()
    
    # REMPLACEMENT PANDAS : Utiliser des listes Python au lieu de DataFrame
    book_data = []
    for book in books:
        book_data.append({
            'id': book.id,
            'title': book.title,
            'content': book.content,
            'genre': book.genre,
            'combined': f"{book.content} {book.genre}"
        })
    
    # TF-IDF
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform([book['combined'] for book in book_data])
    
    # Calculer similarité cosine
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
    
    # Trouver l'index du livre donné
    idx = None
    for i, book in enumerate(book_data):
        if book['id'] == book_id:
            idx = i
            break
    
    if idx is None:
        return Book.objects.none()
    
    # Trier les livres similaires
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:top_n+1]
    
    # Récupérer les IDs
    book_indices = [i[0] for i in sim_scores]
    recommended_ids = [book_data[i]['id'] for i in book_indices]
    return Book.objects.filter(id__in=recommended_ids)

def build_interaction_matrix():
    user_book_data = []

    for user in User.objects.all():
        for book in user.favorite_books.all():
            user_book_data.append((user.id, book.id, 1))

    print("User-Book Data:", user_book_data)

    # REMPLACEMENT PANDAS : Créer une structure de données sans pandas
    if not user_book_data:
        return None

    # Créer un dictionnaire pour la matrice utilisateur-livre
    user_book_dict = defaultdict(dict)
    for user_id, book_id, interaction in user_book_data:
        user_book_dict[user_id][book_id] = interaction

    return user_book_dict

def train_knn_model(user_book_dict):
    if not user_book_dict:
        return None

    # Créer une liste de tous les livres uniques
    all_books = set()
    for books in user_book_dict.values():
        all_books.update(books.keys())
    all_books = sorted(all_books)

    # Créer la matrice manuellement
    matrix_data = []
    user_ids = []
    
    for user_id, books in user_book_dict.items():
        user_vector = [books.get(book_id, 0) for book_id in all_books]
        matrix_data.append(user_vector)
        user_ids.append(user_id)

    if not matrix_data:
        return None

    model = NearestNeighbors(metric='cosine', algorithm='brute')
    model.fit(matrix_data)
    
    return model, matrix_data, user_ids, all_books

def get_user_recommendations(user_id, top_n=5):
    user_book_dict = build_interaction_matrix()
    if not user_book_dict or user_id not in user_book_dict:
        return []

    model, matrix_data, user_ids, all_books = train_knn_model(user_book_dict)
    if not model:
        return []

    # Trouver l'index de l'utilisateur
    try:
        user_index = user_ids.index(user_id)
    except ValueError:
        return []

    # ne pas dépasser le nombre d'utilisateurs existants
    n_neighbors = min(top_n + 1, len(user_ids))

    distances, indices = model.kneighbors(
        [matrix_data[user_index]], n_neighbors=n_neighbors
    )

    neighbor_ids = [user_ids[i] for i in indices[0] if user_ids[i] != user_id]

    recommended_books_ids = []
    for neighbor in neighbor_ids:
        neighbor_books = user_book_dict[neighbor]
        user_books = user_book_dict[user_id]
        
        # Livres que le voisin a mais pas l'utilisateur
        unseen_books = [book_id for book_id in neighbor_books 
                       if neighbor_books[book_id] > 0 and user_books.get(book_id, 0) == 0]
        recommended_books_ids.extend(unseen_books)

    # Éviter les doublons
    recommended_books_ids = list(dict.fromkeys(recommended_books_ids))[:top_n]
    return Book.objects.filter(id__in=recommended_books_ids)