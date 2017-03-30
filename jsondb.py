import os
import re
import json

_cluster_name_re = re.compile(r'^[a-zA-Z0-9]+$')

def _validate_cluster_name(cluster_name):
  if not is_valid_cluster_name(cluster_name):
    raise RuntimeError("empty cluster name")
  
def _validate(db_rec):
  if 'cluster_name' not in db_rec:
    raise RuntimeError('cluster name missing')
  
  if 'cluster_members' not in db_rec:
    raise RuntimeError('cluster members missing')

def _get_cluster_json_db_filename(cluster_name):
  _validate_cluster_name(cluster_name)

  return cluster_name + '.json'

def read_json_db(cluster_name):
  _validate_cluster_name(cluster_name)

  fn = _get_cluster_json_db_filename(cluster_name)
  with open(fn) as f:
    return json.load(f)

def delete_cluster(cluster_name):
  _validate_cluster_name(cluster_name)

  if not exist(cluster_name):
    raise RuntimeError("cluster db not exist")
  fn = _get_cluster_json_db_filename(cluster_name)
  del_fn = fn + '.terminated'
  
  os.rename(fn, del_fn)

def is_valid_cluster_name(cluster_name):
  if not cluster_name:
    return False

  if not _cluster_name_re.match(cluster_name):
    return False
  
  return True

def exist(cluster_name):
  _validate_cluster_name(cluster_name)

  fn = _get_cluster_json_db_filename(cluster_name)
  return os.path.exists(fn) and os.path.isfile(fn)

def create_json_db(cluster_name, members):
  _validate_cluster_name(cluster_name)

  if exist(cluster_name):
    raise RuntimeError("db already exist")
  
  rec = {
    'cluster_name': cluster_name,
    'cluster_members': members
  }

  fn = _get_cluster_json_db_filename(cluster_name)
  with open(fn, 'w') as f:
    f.write(json.dump(rec))

def insert_into_json_db(cluster_name, members):
  _validate_cluster_name(cluster_name)

  if exist(cluster_name):
    rec = read_json_db(cluster_name)
  else:
    rec = {
      'cluster_name': cluster_name,
      'cluster_members': []
    }
  
  old_members = rec['cluster_members']
  old_members_iid = [x['instance_id'] for x in old_members]

  for cur_member in members:
    if cur_member['instance_id'] in old_members_iid:
      raise RuntimeError("duplicated instance id")
  
  rec['cluster_members'] = rec['cluster_members'] + members
  fn = _get_cluster_json_db_filename(cluster_name)
  with open(fn, 'w') as f:
    f.write(json.dumps(rec))
