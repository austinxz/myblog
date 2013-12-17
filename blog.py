import os
import cgi
import urllib
import datetime
import unicodedata
import time
import re

import webapp2
import jinja2

from google.appengine.api import users
from google.appengine.api import images
from google.appengine.ext import db


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class Page():
	previous = 1
	current = 1
	next = 1

class MainPage(webapp2.RequestHandler):
	
	def get(self):
		currentPageNum = int(self.request.get('currentPageNum', "1"))

		if users.get_current_user():
			# 1. List all the blogs 
			usremail = users.get_current_user().email()
			blogs = db.GqlQuery("SELECT * FROM Blog WHERE author = :1 ORDER BY createTime DESC LIMIT 10", usremail)	
			othersblog = db.GqlQuery("SELECT * FROM Blog WHERE author != :1 LIMIT 10", usremail)
			posts = db.GqlQuery("SELECT * FROM Post ORDER BY createTime DESC")
			url = users.create_logout_url(self.request.uri)
			url_linktext = 'Logout'
		else:
			usremail = None
			blogs = db.GqlQuery("SELECT * FROM Blog ORDER BY createTime DESC LIMIT 10")
			othersblog = list()
			posts = db.GqlQuery("SELECT * FROM Post ORDER BY createTime DESC")
			url = users.create_login_url(self.request.uri)
			url_linktext = 'Login'

		_tags = set()
		for post in posts:
			for tag in post.tags:
				_tags.add(tag)

		tags = list(_tags)
		tags.sort()

		# At most 10 pages
		if posts.get():
			postsNum = 0
			for _post in posts:
				postsNum = postsNum + 1
		else:
			postsNum = 0


		page = Page()

		page.current = currentPageNum
		# Previous
		if currentPageNum == 1:
			page.previous = None
		else:
			page.previous = currentPageNum - 1
		# Next
		if currentPageNum * 10 + 1 > postsNum:
			page.next = None
		else:
			page.next = currentPageNum + 1

		postsList = posts[(currentPageNum - 1)* 10 : min(currentPageNum * 10, postsNum)]

		template_values = {
			'page': page,
			'user': users.get_current_user(),
			'blogs': blogs,
			'othersblog':othersblog,
			'posts': postsList,
			'tags': tags,
			'url': url,
			'url_linktext': url_linktext,
		}

		template = JINJA_ENVIRONMENT.get_template('index.html')
		self.response.write(template.render(template_values))


# post obj
class Post(db.Model):
	pid = db.StringProperty(required = True)
	author = db.StringProperty(required = True, indexed = True)
	bname = db.StringProperty(required = True, indexed = True)
	bid = db.StringProperty(required = True)
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

class post(webapp2.RequestHandler):

	def get(self):
		pid = self.request.get('pid')

		post = db.GqlQuery("SELECT * FROM Post WHERE pid = :1", pid)
		if users.get_current_user() and post and post.get().author == users.get_current_user().email():
			edit = True
		else:
			edit = False
		
		if users.get_current_user():
			url = users.create_logout_url(self.request.uri)
			url_linktext = 'Logout'
		else:
			url = users.create_login_url(self.request.uri)
			url_linktext = 'Login'

		template_values = {
			'user': users.get_current_user(),
			'edit': edit,
			'post': post.get(),
			'url': url,
			'url_linktext': url_linktext,
		}

		template = JINJA_ENVIRONMENT.get_template('post.html')
		self.response.write(template.render(template_values))



class newpost(webapp2.RequestHandler):

	def get(self):
		bid = self.request.get('bid')
		blog = db.GqlQuery("SELECT * FROM Blog WHERE bid = :1", bid)

		if users.get_current_user():
			url = users.create_logout_url(self.request.uri)
			url_linktext = 'Logout'
		else:
			url = users.create_login_url(self.request.uri)
			url_linktext = 'Login'

		template_values = {
			'user': users.get_current_user(),
			'url': url,
			'url_linktext': url_linktext,
			'blog': blog.get(),
		}

		template = JINJA_ENVIRONMENT.get_template('newpost.html')
		self.response.write(template.render(template_values))



# handler to create post
class newposthandle(webapp2.RequestHandler):

	def post(self):
		# Create new post
		bid = self.request.get('bid')
		title = self.request.get('title')
		content = self.request.get('content')
		tags = self.request.get('tags')
		img = self.request.get('image')

		blog = db.GqlQuery("SELECT * FROM Blog WHERE bid = :1", bid)
		pid = users.get_current_user().email() + str(datetime.datetime.now())
		post = Post(pid = pid,
					author = users.get_current_user().email(),
					bname = blog.get().bname,
					bid = blog.get().bid,
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
		query_params = {'pid': pid }
		self.redirect('/post?' + urllib.urlencode(query_params))


class editpost(webapp2.RequestHandler):

	def get(self):
		pid = self.request.get('pid')

		post = db.GqlQuery("SELECT * FROM Post WHERE pid = :1", pid)

		template_values = {
			'post': post.get(),
		}

		template = JINJA_ENVIRONMENT.get_template('editpost.html')
		self.response.write(template.render(template_values))

	def post(self):
		newTitle = self.request.get('new_title')
		newContent = self.request.get('new_content')
		pid = self.request.get('pid')
		tags = self.request.get('new_tags')

		if tags:
			newTags = tags.split(',')
		else:
			newTags = list()
		post = db.GqlQuery("SELECT * FROM Post WHERE pid = :1", pid)

		for p in post:
			p.title = newTitle
			p.content = newContent
			p.modifiedTime = datetime.datetime.now()
			p.tags = newTags
			db.put(p)

		time.sleep(1)
		query_params = {'pid': pid }
		self.redirect('/post?' + urllib.urlencode(query_params))
		


class deletepost(webapp2.RequestHandler):

	def get(self):
		pid = self.request.get('pid')

		post = db.GqlQuery("SELECT * FROM Post WHERE pid = :1", pid)
		bid = post.get().bid
		for p in post:
			db.delete(p)

		time.sleep(1)
		query_params = {'bid': bid}
		self.redirect('/blog?' + urllib.urlencode(query_params))



# blog obj
class Blog(db.Model):
	bid = db.StringProperty(required = True)
	author = db.StringProperty(required = True)
	bname = db.StringProperty(required = True, indexed=True)
	createTime = db.DateTimeProperty(required = True, indexed=True)
	modifiedTime = db.DateTimeProperty()

class blog(webapp2.RequestHandler):

	def get(self):
		bid = self.request.get('bid')
		currentPageNum = int(self.request.get('currentPageNum', "1"))

		blog = db.GqlQuery("SELECT * FROM Blog WHERE bid=:1", bid)
		posts = db.GqlQuery("SELECT * FROM Post WHERE bid = :1 ORDER BY createTime DESC", bid)
		if users.get_current_user() and blog.get().author == users.get_current_user().email():
			edit = True
		else:
			edit = False

		if posts.get():
			postsNum = 0
			for _post in posts:
				postsNum = postsNum + 1
		else:
			postsNum = 0

		page = Page()

		page.current = currentPageNum

		if currentPageNum == 1:
			page.previous = None
		else:
			page.previous = currentPageNum - 1

		if currentPageNum * 10 + 1 > postsNum:
			page.next = None
		else:
			page.next = currentPageNum + 1

		postsList = posts[(currentPageNum - 1)* 10 : min(currentPageNum * 10, postsNum)]

		if users.get_current_user():
			url = users.create_logout_url(self.request.uri)
			url_linktext = 'Logout'
		else:
			url = users.create_login_url(self.request.uri)
			url_linktext = 'Login'

		template_values = {
			'user': users.get_current_user(),
			'blog': blog.get(),
			'page': page,
			'edit': edit,
			'posts': postsList,
			'url': url,
			'url_linktext': url_linktext,
		}

		template = JINJA_ENVIRONMENT.get_template('blog.html')
		self.response.write(template.render(template_values))


class newblog(webapp2.RequestHandler):

	def get(self):

		if users.get_current_user():
			url = users.create_logout_url(self.request.uri)
			url_linktext = 'Logout'
		else:
			url = users.create_login_url(self.request.uri)
			url_linktext = 'Login'

		template_values = {
			'user': users.get_current_user(),
			'url': url,
			'url_linktext': url_linktext,
		}

		template = JINJA_ENVIRONMENT.get_template('newblog.html')
		self.response.write(template.render(template_values))

# handler to create new 
class newbloghandle(webapp2.RequestHandler):

	def post(self):
		# Create new post
		bname = self.request.get('bname')

		bid = users.get_current_user().email() + str(datetime.datetime.now())
		blog = Blog(bid = bid,
					author = users.get_current_user().email(),
					bname = bname,
					createTime = datetime.datetime.now(),
					modifiedTime = datetime.datetime.now())
		blog.put()

		time.sleep(1)
		self.redirect('/')

class deleteblog(webapp2.RequestHandler):

	def get(self):
		bid = self.request.get('bid')

		# del blog 
		blog = db.GqlQuery("SELECT * FROM Blog WHERE bid = :1", bid)
		db.delete(blog)

		# then all posts
		posts = db.GqlQuery("SELECT * FROM Post WHERE bid = :1", bid)
		for post in posts:
			db.delete(post)

		time.sleep(1)
		self.redirect('/')




class tags(webapp2.RequestHandler):

	def get(self):
		_tag = self.request.get('tag')
		currentPageNum = int(self.request.get('currentPageNum', "1"))

		posts = db.GqlQuery("SELECT * FROM Post WHERE tags = :1 ORDER BY createTime DESC", _tag)

		if posts.get():
			postsNum = 0
			for _post in posts:
				postsNum = postsNum + 1
		else:
			postsNum = 0
			
		page = Page()

		page.current = currentPageNum

		if currentPageNum == 1:
			page.previous = None
		else:
			page.previous = currentPageNum - 1

		if currentPageNum * 10 + 1 > postsNum:
			page.next = None
		else:
			page.next = currentPageNum + 1

		postsList = posts[(currentPageNum - 1)* 10 : min(currentPageNum * 10, postsNum)]

		if users.get_current_user():
			url = users.create_logout_url(self.request.uri)
			url_linktext = 'Logout'
		else:
			url = users.create_login_url(self.request.uri)
			url_linktext = 'Login'

		template_values = {
			'page': page,
			'tag': _tag,
			'posts': postsList,
			'user': users.get_current_user(),
			'url': url,
			'url_linktext': url_linktext,
		}

		template = JINJA_ENVIRONMENT.get_template('tags.html')
		self.response.write(template.render(template_values))


class Picture(db.Model):
	author = db.StringProperty(required = True)
	image = db.BlobProperty(required = True, default = None)
	uploadTime = db.DateTimeProperty(required = True)


class uploadimg(webapp2.RequestHandler):
	def get(self):
		author = self.request.get('author')

		template_values = {
			'author': author,
		}

		template = JINJA_ENVIRONMENT.get_template('uploadimg.html')
		self.response.write(template.render(template_values))

class uploadimghandle(webapp2.RequestHandler):

	def post(self):
		img = self.request.get('img')
		author = self.request.get('author')

		picture = Picture(author = author,
						  image = db.Blob(img),
						  uploadTime = datetime.datetime.now())
		picture.put()

		self.redirect('/')

class viewPicture(webapp2.RequestHandler):

	def get(self):
		pictures = db.GqlQuery("SELECT * FROM Picture")

		for pic in pictures:
			self.response.headers['Content-Type'] = 'image/png'
			self.response.out.write(pic.image)

class rss(webapp2.RequestHandler):
	
	def get(self):
		bid = self.request.get('bid')
		blog = db.GqlQuery("SELECT * FROM Blog WHERE bid = :1", bid)
		posts = db.GqlQuery("SELECT * FROM Post WHERE bid = :1", bid)

		template_values = {
			'blog': blog.get(),
			'posts': posts,
		}

		template = JINJA_ENVIRONMENT.get_template('rss.xml')
		self.response.write(template.render(template_values))


application = webapp2.WSGIApplication([
	('/', MainPage),
	('/newposthandle', newposthandle),
	('/newbloghandle', newbloghandle),
	('/newpost', newpost),
	('/newblog', newblog),
	('/blog', blog),
	('/post', post),
	('/deleteblog', deleteblog),
	('/deletepost', deletepost),
	('/editpost', editpost),
	('/tags', tags),
	('/rss', rss),
	('/uploadimg', uploadimg),
	('/uploadimghandle', uploadimghandle),
	('/viewPicture', viewPicture),
], debug = True)


