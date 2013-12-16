import os
import cgi
import urllib
import datetime
import unicodedata
import time

from google.appengine.api import users
from google.appengine.ext import db

import webapp2
import jinja2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

# Class used to represent a blog post object.
class Post(db.Model):
	author = db.StringProperty(required = True)
	blogName = db.StringProperty(required = True, indexed = True)
	title = db.StringProperty(required = True, indexed = True)
	content = db.TextProperty(required = True, indexed = False)
	createTime = db.DateTimeProperty(indexed=True)
	modifiedTime = db.DateTimeProperty()
	tags = db.StringListProperty(indexed = True, default = None)

# Class used to represent the blog object.
class Blog(db.Model):
	author = db.StringProperty(required = True)
	blogName = db.StringProperty(required = True, indexed=True)
	createTime = db.DateTimeProperty(required = True, indexed=True)
	modifiedTime = db.DateTimeProperty()

# The main page
class MainPage(webapp2.RequestHandler):
	
	def get(self):
		if users.get_current_user():
			# 1. List all the blogs created by the user
			userEmail = users.get_current_user().email()
			blogs = db.GqlQuery("SELECT * FROM Blog WHERE author = :1 ORDER BY createTime DESC LIMIT 10", userEmail)	
			othersBlogs = db.GqlQuery("SELECT * FROM Blog WHERE author != :1 LIMIT 10", userEmail)
			posts = list()
			url = users.create_logout_url(self.request.uri)
			url_linktext = 'Logout'
		else:
			userEmail = None
			blogs = db.GqlQuery("SELECT * FROM Blog ORDER BY createTime DESC LIMIT 10")
			othersBlogs = list()
			posts = db.GqlQuery("SELECT * FROM Post ORDER BY createTime DESC LIMIT 10")
			url = users.create_login_url(self.request.uri)
			url_linktext = 'Login'

		template_values = {
			'user': users.get_current_user(),
			'blogs': blogs,
			'othersBlogs':othersBlogs,
			'posts': posts,
			'url': url,
			'url_linktext': url_linktext,
		}

		template = JINJA_ENVIRONMENT.get_template('index.html')
		self.response.write(template.render(template_values))

class CreatePostView(webapp2.RequestHandler):

	def get(self):
		template_values = {
			'blogName': self.request.get('blogName'),
		}

		template = JINJA_ENVIRONMENT.get_template('createPost.html')
		self.response.write(template.render(template_values))

class CreateBlogView(webapp2.RequestHandler):

	def get(self):
		template = JINJA_ENVIRONMENT.get_template('createBlog.html')
		self.response.write(template.render())


# The createPost which to handle the create_post operation.
class CreatePostDeal(webapp2.RequestHandler):

	def post(self):
		# Create new post
		
		post = Post(author = users.get_current_user().email(),
					blogName = self.request.get('blogName'),
					title = self.request.get('title'),
					content = self.request.get('content'),
					createTime = datetime.datetime.now(),
					modifiedTime = datetime.datetime.now())

		preTags = self.request.get('tags')
		if len(preTags) > 0 :
			tags = preTags.split(',')
		else:
			tags = list()
		post.tags = tags
		post.put()

		time.sleep(1)
		query_params = {'blogName' : self.request.get('blogName'), 'title': self.request.get('title')}
		self.redirect('/viewPost?' + urllib.urlencode(query_params))

		

# The createBlog which to handle the create_blog operation
class CreateBlogDeal(webapp2.RequestHandler):

	def post(self):
		# Create new post
		blog = Blog(author = users.get_current_user().email(),
					blogName = self.request.get('blogName'),
					createTime = datetime.datetime.now(),
					modifiedTime = datetime.datetime.now())
		blog.put()

		time.sleep(1)
		self.redirect('/')
		

class ViewBlog(webapp2.RequestHandler):

	def get(self):
		blogName = self.request.get('blogName')
		author = self.request.get('author')
		blog = db.GqlQuery("SELECT * FROM Blog WHERE blogName=:1 AND author=:2", blogName, author)
		posts = db.GqlQuery("SELECT * FROM Post WHERE blogName = :1 ORDER BY createTime DESC LIMIT 10", blogName)
		if users.get_current_user() and author == users.get_current_user().email():
			edit = True
		else:
			edit = False
		template_values = {
			'blog': blog.get(),
			'user': users.get_current_user(),
			'edit': edit,
			'posts': posts,
		}

		template = JINJA_ENVIRONMENT.get_template('viewBlog.html')
		self.response.write(template.render(template_values))

class ViewPost(webapp2.RequestHandler):

	def get(self):
		blogName = self.request.get('blogName')
		print("******" + blogName)
		title = self.request.get('title')
		blog = db.GqlQuery("SELECT * FROM Blog WHERE blogName=:1", blogName)
		post = db.GqlQuery("SELECT * FROM Post WHERE blogName=:1 AND title=:2", blogName, title)
		if users.get_current_user() and blog.get().author == users.get_current_user().email():
			edit = True
		else:
			edit = False

		template_values = {
			'author': users.get_current_user().email(),
			'blogName': blogName,
			'edit': edit,
			'title': post.get().title,
			'content': post.get().content.replace('\n', '<br />'),
			'createTime': post.get().createTime,
			'modifiedTime': post.get().modifiedTime,
			'tags': post.get().tags,
		}

		template = JINJA_ENVIRONMENT.get_template('viewPost.html')
		self.response.write(template.render(template_values))

class DeleteBlog(webapp2.RequestHandler):

	def get(self):
		blogName = self.request.get('blogName')
		# 1. Delete the blog in blog table
		blog = db.GqlQuery("SELECT * FROM Blog WHERE blogName = :1 AND author = :2", blogName, users.get_current_user().email())
		db.delete(blog)

		#2. Delete all the post which blogs to that blog.
		posts = db.GqlQuery("SELECT * FROM Post WHERE blogName = :1 AND author = :2", blogName, users.get_current_user().email())
		for post in posts:
			db.delete(post)

		#3. Redirect to the blog list
		time.sleep(1)
		self.redirect('/')

class DeletePost(webapp2.RequestHandler):

	def get(self):
		author = self.request.get('author')
		title = self.request.get('title')
		blogName = self.request.get('blogName')

		posts = db.GqlQuery("SELECT * FROM Post WHERE author=:1 AND title=:2 AND blogName=:3",
			author, title, blogName)
		for post in posts:
			db.delete(post)

		time.sleep(1)
		query_params = {'blogName' : self.request.get('blogName'), 'author': author}
		self.redirect('/viewBlog?' + urllib.urlencode(query_params))


class EditPost(webapp2.RequestHandler):

	def get(self):
		author = self.request.get('author')
		title = self.request.get('title')
		blogName = self.request.get('blogName')
		post = db.GqlQuery("SELECT * FROM Post WHERE author=:1 AND title=:2 AND blogName=:3",
			author, title, blogName)

		template_values = {
			'post': post.get(),
		}

		template = JINJA_ENVIRONMENT.get_template('editPost.html')
		self.response.write(template.render(template_values))

	def post(self):
		newTitle = self.request.get('new_title')
		newContent = self.request.get('new_content')
		blogName = self.request.get('blogName')
		oldTitle = self.request.get('oldTitle')

		post = db.GqlQuery("SELECT * FROM Post WHERE author=:1 AND blogName=:2 AND title=:3",
			users.get_current_user().email(), blogName, oldTitle)

		for p in post:
			p.title = newTitle
			p.content = newContent
			p.modifiedTime = datetime.datetime.now()
			db.put(p)

		time.sleep(1)
		query_params = {'blogName' : self.request.get('blogName'), 'title': newTitle}
		self.redirect('/viewPost?' + urllib.urlencode(query_params))

class TagPosts(webapp2.RequestHandler):

	def get(self):
		tag = self.request.get('t')
		posts = db.GqlQuery("SELECT * FROM Post WHERE :1 in tags", tag)

		template_values = {
			'tag': tag,
			'posts': posts,
		}

		template = JINJA_ENVIRONMENT.get_template('tagPosts.html')
		self.response.write(template.render(template_values))

application = webapp2.WSGIApplication([
	('/', MainPage),
	('/createPostDeal', CreatePostDeal),
	('/createBlogDeal', CreateBlogDeal),
	('/createPostView', CreatePostView),
	('/createBlogView', CreateBlogView),
	('/viewBlog', ViewBlog),
	('/viewPost', ViewPost),
	('/deleteBlog', DeleteBlog),
	('/deletePost', DeletePost),
	('/editPost', EditPost),
	('/tagPosts', TagPosts),
], debug = True)


