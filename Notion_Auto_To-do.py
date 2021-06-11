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

        elif rule_dict[action_attribute_name]['select']['name'] == 'Modify':
            # pair 의 < 만 사용 > 무시하고 뒤에서 불러옴
            if rule_dict[pair_attribute_name]['rich_text'][0]['plain_text'][0] != '<':
                continue

            # pair target id 받아오기 _ 어떤 항목을 어떻게 바꿀지에 대한 rule : pair
            pair_num = rule_dict[pair_attribute_name]['rich_text'][0]['plain_text'][1:]
            pair_target_id_list = find_pair_target_id_list(rule_list,pair_num)


            # 바꿀 항목 받아오기
            change_properties = {}
            for pair_target_id in pair_target_id_list:
                page_properties = get_page(pair_target_id)

                # rule->target의 비어있는 칸은 영향을 주지 않기 위해 제거
                delete_key = []
                for property_key in page_properties.keys():
                    if type(page_properties[property_key][page_properties[property_key]['type']]) == list and len(
                            page_properties[property_key][page_properties[property_key]['type']]) == 0:
                        delete_key.append(property_key)
                    if page_properties[property_key]['type'] == 'checkbox':
                        delete_key.append(property_key)
                    if page_properties[property_key]['type'] == 'title':
                        delete_key.append(property_key)

                for dKey in delete_key:
                    del page_properties[dKey]
                change_properties.update(page_properties)

            # rule에 만족하는 Qurey filter 찾기
            # 저장할 리스트 채우기
            for create_target_dict in rule_dict[relation_attribute_name]['relation']:
                page_properties = get_page(create_target_dict['id'])

                # rule->target의 비어있는 칸은 영향을 주지 않기 위해 제거
                query_filter_list = []
                for property_key in page_properties.keys():
                    if type(page_properties[property_key][page_properties[property_key]['type']]) == list and len(page_properties[property_key][page_properties[property_key]['type']])==0:
                        continue
                    if page_properties[property_key]['type'] == 'checkbox':
                        continue
                    if page_properties[property_key]['type'] == 'title':
                        continue
                    if page_properties[property_key]['type'] in equals_type:
                        query_filter = {"property": property_key, page_properties[property_key]['type']:{
                            'equals': page_properties[property_key][page_properties[property_key]['type']]['name']}}
                        query_filter_list.append(query_filter)
                    elif page_properties[property_key]['type'] in contains_type:
                        for content in page_properties[property_key][page_properties[property_key]['type']]:
                            query_filter = {"property": property_key, page_properties[property_key]['type']: {
                                'contains': content['name']}}
                            query_filter_list.append(query_filter)
                    else :
                        print("error - query filter")

                data = {'filter' : {'and': query_filter_list}}
                res = requests.post(URL + 'databases/' + target_table_id + '/query', headers=post_headers,data=json.dumps(data))
                for page_data in res.json()['results']:

                    state = False
                    for pKey in page_data["properties"].keys():
                        if page_data["properties"][pKey]['id'] == target_relation_attribute_id:
                            if len(page_data["properties"][pKey]['relation']) != 0:
                                state = True
                                break
                    if state:
                        continue
                    data = {"properties": change_properties}
                    print(page_data['id'])
                    res = requests.patch(URL + 'pages/' + page_data['id'], headers=post_headers, data=json.dumps(data))

        else:
            print('error: rule-action')
