from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, DeleteView, UpdateView, edit
from django import forms
from django.urls import reverse_lazy, reverse
from django.views import View
from django.http.response import JsonResponse
from django.conf import settings
from pprint import pprint

from .forms import AnswerQuestionFormSet, AnswerQuestionForm
from ..models import CustomUserModel, TagModel, QuestionModel, EntrySheetesModel, CompanyHomepageURLModel
from ..esuits_utils.newsapi import newsapi
from ..esuits_utils.wordcloudapi.get_wordcloud import get_wordcloud
# Create your views here.


class EsEditView(View):
    '''
    ESの質問に回答するページ
    '''

    # 過去に投稿したポストのうち関連するものを取得
    def _get_related_posts_list(self, request, es_id):
        post_set = QuestionModel.objects.filter(entry_sheet=es_id)
        all_posts_by_login_user = QuestionModel.objects.filter(entry_sheet__author=request.user)

        related_posts_list = [
            all_posts_by_login_user
            .filter(tags__in=post.tags.all())
            .exclude(pk=post.pk)
            for post in post_set
        ]
        return related_posts_list

    # 関連するニュースの取得 (いまはダミー)
    def _get_news_list(self, request, es_group_id):
        news_list = [
            {'title': 'ダミーニュース1', 'url': 'https://news.yahoo.co.jp/pickup/6375312'},
            {'title': 'ダミーニュース2', 'url': 'https://news.yahoo.co.jp/pickup/6375301'},
        ]
        return news_list

    # 企業の情報を取得
    def _get_company_info(self, request, es_id):
        es_info = EntrySheetesModel.objects.get(pk=es_id)
        company_url_info = CompanyHomepageURLModel.objects.get(pk=es_info.homepage_url.pk)
        company_url = company_url_info.homepage_url

        # 現状デプロイ時にワードクラウドは使用しない
        if settings.DEBUG:
            print('開発環境')
            wordcloud_path = get_wordcloud(company_url)
            company_info = {"wordcloud_path": wordcloud_path[1:]}
        else:
            wordcloud_path = '/static/esuits/images/kanban_jyunbi.png'
            company_info = {"wordcloud_path": wordcloud_path}
        return company_info

    # 回答の文字数を計算
    def _get_char_num(self, question_form):
        return len(question_form.answer)
    
    def get(self, request, es_id):
        template_name = 'esuits/es_edit.html'
        if EntrySheetesModel.objects.filter(pk=es_id).exists():
            # ESの存在を確認
            es_info = EntrySheetesModel.objects.get(pk=es_id)

            if (es_info.author == request.user):
                # 指定されたESが存在し，それが自分のESの場合
                post_set = QuestionModel.objects.filter(entry_sheet=es_id).order_by('pk')
                formset = AnswerQuestionFormSet(instance=es_info)

                # 関連したポスト一覧
                related_posts_list = self._get_related_posts_list(request, es_id)
                # ニュース関連
                news_list = newsapi.get_news(es_info.company)
                # 企業の情報(ワードクラウドなど)
                '''
                下記のコードだと「先に画面遷移してからワードクラウド作成」ができない
                company_info = self._get_company_info(request, es_id)
                '''
                # company_info(= 作成されたワードクラウドのパス)の取得はフロント側でやる
                company_info = None

                context = {
                    'message': 'OK',
                    'es_info': es_info,
                    'formset_management_form': formset.management_form,
                    'zipped_posts_info': zip(post_set, formset, related_posts_list),
                    'news_list': news_list,
                    'company_info': company_info,
                    'es_group_id': es_id,
                    'num_related_posts': len(related_posts_list)
                }
                # return render(request, template_name, context)
            else:
                # 指定されたESが存在するが，それが違う人のESの場合
                context = {
                    'message': '違う人のESなので表示できません',
                    'es_info': {},
                    'zipped_posts_info': (),
                }
                # return render(request, template_name, context)
        else:
            # 指定されたESが存在しない場合
            context = {
                'message': '指定されたESは存在しません',
                'es_info': {},
                'zipped_posts_info': (),
            }
        return render(request, template_name, context)

    def post(self, request, es_id):
        template_name = 'esuits/es_edit.html'

        if EntrySheetesModel.objects.filter(pk=es_id).exists():
            # ESの存在を確認
            es_info = EntrySheetesModel.objects.get(pk=es_id)

            if (es_info.author == request.user):
                # 指定されたESが存在し，それが自分のESの場合
                post_set = QuestionModel.objects.filter(entry_sheet=es_id)
                formset = AnswerQuestionFormSet(data=request.POST, instance=es_info)
                forms_ = formset.save(commit=False)
                
                if formset.is_valid():
                    for form in forms_:
                        form.char_num = self._get_char_num(form)
                        form.save()
                    formset.save()
                    return redirect('esuits:home')

                # 関連したポスト一覧
                related_posts_list = self._get_related_posts_list(request, es_id)

                # ニュース関連
                news_list = newsapi.get_news(es_info.company)

                # 企業の情報(ワードクラウドなど)
                company_info = self._get_company_info(request, es_id)

                context = {
                    'message': 'OK',
                    'es_info': es_info,
                    'formset_management_form': formset.management_form,
                    'zipped_posts_info': zip(post_set, formset, related_posts_list),
                    'news_list': news_list,
                    'company_info': company_info,
                }
                return render(request, template_name, context)
            else:
                # 指定されたESが存在するが，それが違う人のESの場合
                context = {
                    'message': '違う人のESなので表示できません',
                    'es_info': {},
                    'zipped_posts_info': (),
                }
                return render(request, template_name, context)
        else:
            # 指定されたESが存在しない場合
            context = {
                'message': '指定されたESは存在しません',
                'es_info': {},
                'zipped_posts_info': (),
            }
            return render(request, template_name, context)


def get_related_post(request):
    print(request.GET.get('pk', ''))
    pk = request.GET.get('pk', '')
    es = QuestionModel.objects.get(pk=pk)
    print(es.question, es.answer, sep='¥n')
    return JsonResponse({'question': es.question, 'answer': es.answer})


def get_wordcloud_path(request):
    print('get_wordcloud_pathを開始')
    print(request.GET.get('es_group_id', ''))
    es_id = request.GET.get('es_group_id', '')
    es_info = EntrySheetesModel.objects.get(pk=es_id)
    company_url_info = CompanyHomepageURLModel.objects.get(homepage_url=es_info.homepage_url)
    company_url = company_url_info.homepage_url

    # 現状デプロイ時にワードクラウドは使用しない
    if not settings.DEBUG:
        print('本番環境')
        return JsonResponse({'image_path': '/static/esuits/images/kanban_jyunbi.png'})

    # 以下開発環境
    # CompanyHomepageURLModelにwordcloud_pathが存在している場合はその画像のパスを取り出す
    try:
        print(company_url + ' already exists')
        wordcloud_path = CompanyHomepageURLModel\
            .objects.get(homepage_url=company_url).word_cloud_path

    # 存在しない場合は新しくワードクラウドを作成
    except CompanyHomepageURLModel.DoesNotExist:
        try:
            wordcloud_path = get_wordcloud(company_url)[1:]
            print(wordcloud_path)
            # データベースに保存

            new_word_cloud = CompanyHomepageURLModel(company=es_info.company,
                    homepage_url=company_url, word_cloud_path=wordcloud_path)
            new_word_cloud.save()
            print('created new word cloud')
        except:
            print('error from word_cloud')
            return JsonResponse({'image_path': '/static/esuits/images/wordcloud_failed.png'})

    # return JsonResponse({'image_path': wordcloud_path})
    homepage_url_record = CompanyHomepageURLModel.objects.get(homepage_url=company_url)
    wordcloud_path = homepage_url_record.word_cloud_path
    if wordcloud_path is None or wordcloud_path == 'dummy_path':
        wordcloud_path = get_wordcloud(company_url)[1:]
        # CompanyHomepageURLModelを更新
        homepage_url_record.word_cloud_path = wordcloud_path
        homepage_url_record.save()
    return JsonResponse({'image_path': wordcloud_path})
