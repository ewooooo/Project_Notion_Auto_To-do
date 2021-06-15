import requests, json
import datetime

now = datetime.datetime.now()
nowTime = now.strftime('%H:%M')
days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
day = days[datetime.datetime.today().weekday()]
nowDate = now.strftime('%Y-%m-%d')
tomorrow = (datetime.datetime.today() + datetime.timedelta( days=1)).strftime('%Y-%m-%d')
##########################################

# 토큰 및 DB id 불러오기
f = open("mydata", 'r')
rule_table_id = f.readline().rstrip()
target_table_id = f.readline().rstrip()
token = 'Bearer '+f.readline().rstrip()
f.close()

# version dependency & rule table attribute
Notion_Version = '2021-05-13'
URL = 'https://api.notion.com/v1/'
get_headers = {'Authorization' : token,'Notion-Version' : Notion_Version}
post_headers = {'Authorization' : token,'Notion-Version' : Notion_Version, 'Content-Type': 'application/json'}

action_attribute_name = '행동'
cycle_attribute_name = '주기'
pair_attribute_name = 'Pair'
active_time_attribute_name = 'Active Time'
relation_attribute_name = 'target'
active_attribute_name = 'active'
InTime_attribute_name = 'In Time'
Auto_attribute_name = 'Auto'

equals_type = ['title', 'rich_text', 'url', 'email', 'phone', 'number','checkbox','select','date', 'created_time', 'last_edited_time']
contains_type= ['multi_select','People','relation']
###################################################################################################################

# 타겟쪽 relation 중 rule과 연결된 속성 id 추출
target_relation_attribute_id = ''
res = requests.get( URL +'databases/'+target_table_id, headers=get_headers)
if res.status_code == 200:
    target_properties_dict = res.json()['properties']
    for key in target_properties_dict.keys():
        if target_properties_dict[key]['type'] == 'relation':
            if target_properties_dict[key]['relation']['database_id'].replace('-','') == rule_table_id :
                target_relation_attribute_id = target_properties_dict[key]['id']


def get_page(page_id):
    res = requests.get(URL + 'pages/' + page_id, headers=get_headers)
    if res.status_code == 200:

        page_properties = res.json()['properties']
        for page_property_key in page_properties.keys():
            if page_properties[page_property_key]['id'] == target_relation_attribute_id:
                del page_properties[page_property_key]
                break

        del page_properties[Auto_attribute_name]



    return page_properties

def rule_active_check(rule_dict):
    if not rule_dict[active_attribute_name]['checkbox']:
        return False
    if rule_dict[active_time_attribute_name]['rich_text'][0]['plain_text'][:3] != nowTime[:3]: #__:_x 비교 1분 단위 무시.
         return False
    rule_days = []
    for ruleDay_dict in rule_dict[cycle_attribute_name]['multi_select']:
        rule_days.append(ruleDay_dict['name'])
    if not day in rule_days and not 'Everyday' in rule_days:
        return False
    return True

def find_pair_target_id_list(rule_list,pair_num):
    result_list = []
    for rule_page in rule_list:
        rule_dict = rule_page['properties']
        if(len(rule_dict[pair_attribute_name]['rich_text'])!= 0):
            if rule_dict[pair_attribute_name]['rich_text'][0]['plain_text'] == '>' + pair_num:
                for create_target_dict in rule_dict[relation_attribute_name]['relation']:
                    result_list.append(create_target_dict['id'])
    return result_list
# rule 적용 start
data = {} ## 정렬추가하기
res = requests.post(URL +'databases/'+rule_table_id+'/query',headers = post_headers, data=json.dumps(data))
if res.status_code == 200:
    rule_list = res.json()['results']
    for rule_page in rule_list:
        rule_dict = rule_page['properties']
        if not rule_active_check(rule_dict):
            continue
        if rule_dict[action_attribute_name]['select']['name'] == 'Create':
            for create_target_dict in rule_dict[relation_attribute_name]['relation']:
                page_properties = get_page(create_target_dict['id'])
                result_data = nowDate if len(rule_dict[active_time_attribute_name]['rich_text'][0]['plain_text']) == 5 else tomorrow
                page_properties[InTime_attribute_name]["date"]["start"] = result_data + page_properties[InTime_attribute_name]["date"]["start"][10:]
                page_properties[InTime_attribute_name]["date"]["end"] = result_data + page_properties[InTime_attribute_name]["date"]["start"][10:]
                data = {"parent":{"database_id":target_table_id},"properties":page_properties}
                res = requests.post(URL + 'pages', headers=post_headers,data=json.dumps(data))
                if res.status_code == 200:
                    print("created - " + res.json()['id'])
                else:
                    print("fail created\n" + page_properties)

        else:
            print('error: rule-action')
