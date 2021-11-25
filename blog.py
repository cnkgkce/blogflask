from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps


app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "ybblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
mysql = MySQL(app)  #Mysql ile app bağdaştırılır, bağlantı kurulur 

#Login kontrolünü sağlayan decarator
def login_required(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        if "logged_in" in session:
            return f(*args,**kwargs)
        else:
            flash("Bu sayfayı görüntülemek için giriş yapın","danger")
            redirect(url_for("login"))

    return decorated_function

#Kullanıcı kayıt formu 

class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.Length(min=4,max=25)])
    username = StringField("Kullanıcı Adı",validators=[validators.Length(min=4,max=25)])
    email = StringField("Email Adresi",validators=[validators.Email(message="Lütfen geçerli bir email adresi girin")])
    password = PasswordField("Parola",validators=[
        validators.Length(min=4,max=25),
        validators.DataRequired(message="Lütfen parola giriniz"),
        validators.EqualTo(fieldname="confirm",message="Parolanız uyuşmuyor")
    ])
    confirm = PasswordField("Parola Doğrula")


class LoginForm(Form): #İçeriye aldığın Form aslında Formdan inherit işlemi demektir 
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")


class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators=[validators.length(5,100)])
    content = TextAreaField("İçerik",validators=[validators.length(10)])


#Routing 

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/articles/<string:id>')
def detail(id):
    return "Article id" +" "+id



@app.route('/register',methods=["GET","POST"])
def register():
    form = RegisterForm(request.form) #request.form ile form içerisindeki tüm bilgiler buraya gelir 
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        
        cursor = mysql.connection.cursor() #cursor oluştu(db üzerinde işlem yapmak için cursor şart)

        query = "Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"

        cursor.execute(query,(name,email,username,password)) #tuple' ın olayı %s lerle yer değiştirmektir. 
        mysql.connection.commit() #veritabanında değişiklik yapıyorsak(ekleme,güncelleme veya silme) commit yapmalıyız
        cursor.close()
        flash("Kayıt Başarılı!","success")
        return redirect(url_for("login"))  #url_for(function_name) metodu içerisine parametre olarak aldığı fonksiyonla ilişkili URL'i oluşturur
    else:
        return render_template("register.html",form=form)




@app.route("/login",methods=["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST" and form.validate():
        username = form.username.data
        password_entered = form.password.data
        cursor = mysql.connection.cursor()

        query = "Select * From users where username= %s"
        result = cursor.execute(query,(username,)) #sonuna virgül kısmı önemli yoksa tuple olduğunu anlayamaz 

        if result > 0:
            data = cursor.fetchone() #kullanıcıya ait tüm bilgileri getirir. Dönen data bir dictionarydir. 
            real_password = data["password"] # Burada bir dictionary dönmesnin sebebi config kısmında DictCursor yazmıştık.
            if sha256_crypt.verify(password_entered,real_password): #girilen parola ile gerçek parolayı karşılaştırıyor 
                flash("Giriş Başarılı","success")

                session["logged_in"] = True #buradaki sessionu renderla göndermek zorunda değiliz. Sessiona her yerden erişebiliriz
                session["username"] = username #buradaki sessionu renderla göndermek zorunda değiliz. Sessiona her yerden erişebiliriz

                redirect(url_for("index"))
            else:
                flash("Parola hatalı","danger")
                redirect(url_for("index"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor","danger")
            redirect(url_for("login"))

    return render_template("login.html",form=form)



@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))



@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()

    query = "Select * From articles where author= %s"

    result = cursor.execute(query,(session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        return render_template("dashboard.html")

        

@app.route("/addarticle",methods=["GET","POST"])
@login_required
def addArticle():
    form = ArticleForm(request.form)
    if request.method =="POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()

        query = "INSERT INTO articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(query,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()

        flash("Makale başarıyla eklendi","success")
        return redirect(url_for("dashboard"))



    return render_template("addarticle.html",form=form)




@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()

    query = "SELECT * FROM articles"

    result = cursor.execute(query)
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles=articles)
    
    else:
        return render_template("articles.html")



#Detay sayfasi 

@app.route("/article/<int:id>")
def article(id):
    cursor = mysql.connection.cursor()

    query = "Select * From articles where id = %s"

    result = cursor.execute(query,(id,))
    
    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article=article)
    else:
        return render_template("article.html")


#Makale silme

@app.route("/delete/<int:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()

    query = "Select * from articles where author = %s and id= %s"

    result = cursor.execute(query,(session["username"],id))

    if result > 0 :
        query2 = "Delete from articles where id=%s"
        cursor.execute(query2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya bu işleme yetkiniz yok","danger")
        return redirect(url_for("index"))


#Makale Güncelleme 

@app.route("/edit/<int:id>",methods=["GET","POST"])
@login_required
def update(id):
    if request.method == "GET":
        #Önce makaleyi görüntülüyor olmamız lazım 
        cursor = mysql.connection.cursor()
        query1 = "Select * from articles where id = %s"
        cursor.execute(query1,(id,))
        
        article = cursor.fetchone()

        form = ArticleForm()
        form.title.data = article["title"]
        form.content.data = article["content"]
        return render_template("edit.html",form=form)
    else:
        #Request post ise artık güncelleme işlemi yapılacak demektir
        cursor = mysql.connection.cursor()
        form = ArticleForm(request.form)
        query2 = "Update articles Set title = %s,content = %s where id = %s"
        newTitle = form.title.data
        newContent = form.content.data


        cursor.execute(query2,(newTitle,newContent,id))

        mysql.connection.commit()
        
        flash("Güncelleme başarılı","success")
        return redirect(url_for("dashboard"))



#Arama URL

@app.route("/search",methods=["GET","POST"])
@login_required
def search():
    if request.method =="GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword") # input alanından değer alındı
        cursor = mysql.connection.cursor()
        query = "Select * from articles where title like '%" + keyword + "%'"

        result = cursor.execute(query)

        if result == 0:
            flash("Aranan Kelimeye uygun makale bulunamadı","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles=articles) #aynı articles aynı zamanda articles() metodundan da dönüyor 





if __name__ == '__main__':
    app.run(debug=True)