import os
import cgi
import urllib
import datetime
import unicodedata
import time
import re

from google.appengine.api import users
from google.appengine.ext import db

import webapp2
import jinja2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class Page():
	previousPage = 1
	currentPage = 1
	nextPage = 1

# Class used to represent a blog post object.
class Post(db.Model):
	postId = db.StringProperty(required = True)
	author = db.StringProperty(required = True, indexed = True)
	blogName = db.StringProperty(required = True, indexed = True)
	blogId = db.StringProperty(required = True)
	title = db.StringProperty(required = True, indexed = True)
	content = db.TextProperty(required = True, indexed = False)
	createTime = db.DateTimeProperty(indexed=True)
	modifiedTime = db.DateTimeProperty()
	tags = db.StringListProperty(default=None, indexed = True)

	def contentParser(self):
		result = re.sub(r'(http[s]?://[^,\s\n]*)', '<a href="\\1">\\1</a>', self.content)
		result = re.sub(r'<a href="(http[s]?://[^,\s\n]*[(.jpg)(.png)(.gif)])">.*</a>', '<img src="\\1" width="300" height="300">', result)
		result = result.replace('\n', '<br />')
		return result
	
	def contentPreview(self):
		_content = self.contentParser()
		return _content[0 : 499]

	def tagsStr(self):
		tags = ""
		for tag in self.tags:
			tags = tags + tag + ","
		return tags[:len(tags) - 1]

# Class used to represent the blog object.
class Blog(db.Model):
	blogId = db.StringProperty(required = True)
	author = db.StringProperty(required = True)
	blogName = db.StringProperty(required = True, indexed=True)
	createTime = db.DateTimeProperty(required = True, indexed=True)
	modifiedTime = db.DateTimeProperty()

# The main page
class MainPage(webapp2.RequestHandler):
	
	def get(self):
		currentPageNum = int(self.request.get('currentPageNum', "1"))

		if users.get_current_user():
			# 1. List all the blogs created by the user
			userEmail = users.get_current_user().email()
			blogs = db.GqlQuery("SELECT * FROM Blog WHERE author = :1 ORDER BY createTime DESC LIMIT 10", userEmail)	
			othersBlogs = db.GqlQuery("SELECT * FROM Blog WHERE author != :1 LIMIT 10", userEmail)
			posts = db.GqlQuery("SELECT * FROM Post ORDER BY createTime DESC")
			url = users.create_logout_url(self.request.uri)
			url_linktext = 'Logout'
		else:
			userEmail = None
			blogs = db.GqlQuery("SELECT * FROM Blog ORDER BY createTime DESC LIMIT 10")
			othersBlogs = list()
			posts = db.GqlQuery("SELECT * FROM Post ORDER BY createTime DESC")
			url = users.create_login_url(self.request.uri)
			url_linktext = 'Login'

		_tags = set()
		for post in posts:
			for tag in post.tags:
				_tags.add(tag)

		tags = list(_tags)
		tags.sort()

		# At most 10 pages at the home page.
		# 1. Get the total number of page
		if posts.get():
			postsNum = 0
			for _post in posts:
				postsNum = postsNum + 1
		else:
			postsNum = 0

		# 2. Create a page object, and fill in the requested attributes.
		page = Page()
		# 2.1 Current page
		page.currentPage = currentPageNum
		# 2.2 Previous page
		if currentPageNum == 1:
			page.previousPage = None
		else:
			page.previousPage = currentPageNum - 1
		# 2.3 Next page
		if currentPageNum * 10 + 1 > postsNum:
			page.nextPage = None
		else:
			page.nextPage = currentPageNum + 1

		# 3. Compute the posts for current page.
		postsList = posts[(currentPageNum - 1)* 10 : min(currentPageNum * 10, postsNum)]

		template_values = {
			'page': page,
			'user': users.get_current_user(),
			'blogs': blogs,
			'othersBlogs':othersBlogs,
			'posts': postsList,
			'tags': tags,
			'url': url,
			'url_linktext': url_linktext,
		}

		template = JINJA_ENVIRONMENT.get_template('index.html')
		self.response.write(template.render(template_values))

class CreatePostView(webapp2.RequestHandler):

	def get(self):
		blogId = self.request.get('blogId')
		blog = db.GqlQuery("SELECT * FROM Blog WHERE blogId = :1", blogId)
		template_values = {
			'blog': blog.get(),
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
		blogId = self.request.get('blogId')
		title = self.request.get('title')
		content = self.request.get('content')
		tags = self.request.get('tags')

		blog = db.GqlQuery("SELECT * FROM Blog WHERE blogId = :1", blogId)
		postId = users.get_current_user().email() + str(datetime.datetime.now())
		post = Post(postId = postId,
					author = users.get_current_user().email(),
					blogName = blog.get().blogName,
					blogId = blog.get().blogId,
					title = title,
					content = content,
					createTime = datetime.datetime.now(),
					modifiedTime = datetime.datetime.now())

		if len(tags) > 0 :
			tags = tags.split(',')
		else:
			tags = list()
		post.tags = tags
		post.put()

		time.sleep(1)
		query_params = {'postId': postId }
		self.redirect('/viewPost?' + urllib.urlencode(query_params))


# The createBlog which to handle the create_blog operation
class CreateBlogDeal(webapp2.RequestHandler):

	def post(self):
		# Create new post
		blogName = self.request.get('blogName')

		blogId = users.get_current_user().email() + str(datetime.datetime.now())
		blog = Blog(blogId = blogId,
					author = users.get_current_user().email(),
					blogName = blogName,
					createTime = datetime.datetime.now(),
					modifiedTime = datetime.datetime.now())
		blog.put()

		time.sleep(1)
		self.redirect('/')
		

class ViewBlog(webapp2.RequestHandler):

	def get(self):
		blogId = self.request.get('blogId')
		currentPageNum = int(self.request.get('currentPageNum', "1"))

		blog = db.GqlQuery("SELECT * FROM Blog WHERE blogId=:1", blogId)
		posts = db.GqlQuery("SELECT * FROM Post WHERE blogId = :1 ORDER BY createTime DESC", blogId)
		if users.get_current_user() and blog.get().author == users.get_current_user().email():
			edit = True
		else:
			edit = False


		# At most 10 pages at the home page.
		# 1. Get the total number of page
		if posts.get():
			postsNum = 0
			for _post in posts:
				postsNum = postsNum + 1
		else:
			postsNum = 0

		# 2. Create a page object, and fill in the requested attributes.
		page = Page()
		# 2.1 Current page
		page.currentPage = currentPageNum
		# 2.2 Previous page
		if currentPageNum == 1:
			page.previousPage = None
		else:
			page.previousPage = currentPageNum - 1
		# 2.3 Next page
		if currentPageNum * 10 + 1 > postsNum:
			page.nextPage = None
		else:
			page.nextPage = currentPageNum + 1

		# 3. Compute the posts for current page.
		postsList = posts[(currentPageNum - 1)* 10 : min(currentPageNum * 10, postsNum)]

		template_values = {
			'blog': blog.get(),
			'page': page,
			'edit': edit,
			'posts': postsList,
		}

		template = JINJA_ENVIRONMENT.get_template('viewBlog.html')
		self.response.write(template.render(template_values))



class ViewPost(webapp2.RequestHandler):

	def get(self):
		postId = self.request.get('postId')

		post = db.GqlQuery("SELECT * FROM Post WHERE postId = :1", postId)
		if users.get_current_user() and post and post.get().author == users.get_current_user().email():
			edit = True
		else:
			edit = False

		template_values = {
			'edit': edit,
			'post': post.get(),
		}

		template = JINJA_ENVIRONMENT.get_template('viewPost.html')
		self.response.write(template.render(template_values))

class DeleteBlog(webapp2.RequestHandler):

	def get(self):
		blogId = self.request.get('blogId')

		# 1. Delete the blog in blog table
		blog = db.GqlQuery("SELECT * FROM Blog WHERE blogId = :1", blogId)
		db.delete(blog)

		#2. Delete all the post which blogs to that blog.
		posts = db.GqlQuery("SELECT * FROM Post WHERE blogId = :1", blogId)
		for post in posts:
			db.delete(post)

		#3. Redirect to the blog list
		time.sleep(1)
		self.redirect('/')

class DeletePost(webapp2.RequestHandler):

	def get(self):
		postId = self.request.get('postId')

		post = db.GqlQuery("SELECT * FROM Post WHERE postId = :1", postId)
		blogId = post.get().blogId
		for p in post:
			db.delete(p)

		time.sleep(1)
		query_params = {'blogId': blogId}
		self.redirect('/viewBlog?' + urllib.urlencode(query_params))


class EditPost(webapp2.RequestHandler):

	def get(self):
		postId = self.request.get('postId')

		post = db.GqlQuery("SELECT * FROM Post WHERE postId = :1", postId)

		template_values = {
			'post': post.get(),
		}

		template = JINJA_ENVIRONMENT.get_template('editPost.html')
		self.response.write(template.render(template_values))

	def post(self):
		newTitle = self.request.get('new_title')
		newContent = self.request.get('new_content')
		postId = self.request.get('postId')
		tags = self.request.get('new_tags')

		if tags:
			newTags = tags.split(',')
		else:
			newTags = list()
		post = db.GqlQuery("SELECT * FROM Post WHERE postId = :1", postId)

		for p in post:
			p.title = newTitle
			p.content = newContent
			p.modifiedTime = datetime.datetime.now()
			p.tags = newTags
			db.put(p)

		time.sleep(1)
		query_params = {'postId': postId }
		self.redirect('/viewPost?' + urllib.urlencode(query_params))

class TagPosts(webapp2.RequestHandler):

	def get(self):
		_tag = self.request.get('tag')
		currentPageNum = int(self.request.get('currentPageNum', "1"))

		posts = db.GqlQuery("SELECT * FROM Post WHERE tags = :1 ORDER BY createTime DESC", _tag)

		# At most 10 pages at the home page.
		# 1. Get the total number of page
		if posts.get():
			postsNum = 0
			for _post in posts:
				postsNum = postsNum + 1
		else:
			postsNum = 0
			
		# 2. Create a page object, and fill in the requested attributes.
		page = Page()
		# 2.1 Current page
		page.currentPage = currentPageNum
		# 2.2 Previous page
		if currentPageNum == 1:
			page.previousPage = None
		else:
			page.previousPage = currentPageNum - 1
		# 2.3 Next page
		if currentPageNum * 10 + 1 > postsNum:
			page.nextPage = None
		else:
			page.nextPage = currentPageNum + 1

		# 3. Compute the posts for current page.
		postsList = posts[(currentPageNum - 1)* 10 : min(currentPageNum * 10, postsNum)]

		template_values = {
			'page': page,
			'tag': _tag,
			'posts': postsList
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


