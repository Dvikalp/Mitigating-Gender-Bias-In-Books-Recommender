# Install MIP and Gurobipy for optimization purpose
# ! pip install mip
# ! python -m pip install gurobipy==9.1.2
# install Cornac framework for RecSys
# ! pip install cornac

"""## Config"""

# import packages
import os
import numpy as np
from collections import defaultdict
from tqdm import tqdm
import argparse

from itertools import product
from sys import stdout as out
from mip import Model, xsum, maximize, BINARY

import cornac
from cornac.eval_methods import BaseMethod
from cornac.models import MostPop, UserKNN, ItemKNN, MF, PMF, BPR, NeuMF, WMF, HPF, CVAE, VAECF, NMF
from cornac.metrics import Precision, Recall, NDCG, AUC, MAP, FMeasure, MRR
from cornac.data import Reader

# ### Arguments ###
# parser = argparse.ArgumentParser(description='exCPFair')
# parser.add_argument('-d','--dataset', help='name of dataset', required=True)
# args = parser.parse_args() # Parse the argument

"""## Download datasets, user, and item groups"""

# download datasets: train, test, tune
def download_dataset():
  ds_root_path = "datasets/"
  for dataset in ds_names:
    dataset_path = os.path.join(ds_root_path, dataset)

    if not os.path.isdir(dataset_path):
      os.makedirs(dataset_path)
      print("Directory '%s' is created." % dataset_path)
    else:
      print("Directory '%s' is exist." % dataset_path)

    # -nc: skip downloads that would download to existing files.

    try:
      os.system(f"wget -P {dataset_path} -nc https://raw.githubusercontent.com/rahmanidashti/exCPFair/main/datasets/{dataset}/{dataset}_train.txt")
      os.system(f"wget -P {dataset_path} -nc https://raw.githubusercontent.com/rahmanidashti/exCPFair/main/datasets/{dataset}/{dataset}_test.txt")
      os.system(f"wget -P {dataset_path} -nc https://raw.githubusercontent.com/rahmanidashti/exCPFair/main/datasets/{dataset}/{dataset}_tune.txt")
      print(f"{dataset}: The train, tune, and test sets downloaded.")
    except Expception as e:
      print(e)

# dowanload user groups: active and inactive
def download_user_groups():
  user_root_path = "user_groups/"
  for dataset in ds_names:
    for ugroup in ds_users:
      user_groups_path = os.path.join(user_root_path, dataset, ugroup)

      if not os.path.isdir(user_groups_path):
        os.makedirs(user_groups_path)
        print("Directory '%s' is created." % user_groups_path)
      else:
        print("Directory '%s' is exist." % user_groups_path)

      # -nc: skip downloads that would download to existing files.

      try:
        os.system(f"wget -P {user_groups_path} https://raw.githubusercontent.com/rahmanidashti/exCPFair/main/datasets/{dataset}/groups/users/{ugroup}/active_ids.txt")
        os.system(f"wget -P {user_groups_path} https://raw.githubusercontent.com/rahmanidashti/exCPFair/main/datasets/{dataset}/groups/users/{ugroup}/inactive_ids.txt")
        print(f"{dataset}: User groups on '{ugroup}' downloaded.")
      except Exception as e:
        print(e)

# dowanload item groups: short-head and long-tail
def download_item_groups():
  item_root_path = "item_groups/"
  for dataset in ds_names:
    for igroup in ds_items:
      item_groups_path = os.path.join(item_root_path, dataset, igroup)

      if not os.path.isdir(item_groups_path):
        os.makedirs(item_groups_path)
        print("Directory '%s' is created." % item_groups_path)
      else:
        print("Directory '%s' is exist." % item_groups_path)
      
      # -nc: skip downloads that would download to existing files.
    try:
      os.system(f"wget -P {item_groups_path} -nc https://raw.githubusercontent.com/rahmanidashti/exCPFair/main/datasets/{dataset}/groups/items/{igroup}/shorthead_items.txt")
      os.system(f"wget -P {item_groups_path} -nc https://raw.githubusercontent.com/rahmanidashti/exCPFair/main/datasets/{dataset}/groups/items/{igroup}/longtail_items.txt")
      print(f"{dataset}: Item groups on '{igroup}' downloaded.")
    except Exception as e:
      print(e)

"""## Run Config"""

ds_names = ["BookCrossing"]
ds_users = ['20']
ds_items = ['020']

###
no_user_groups = 2
no_item_groups = 2
topk = 50

download_dataset()
download_user_groups()
download_item_groups()

"""## Load `Cornac` data and model"""

def read_data(dataset):

  reader = Reader()
  train_data = reader.read(fpath=f"datasets/{dataset}/{dataset}_train.txt", fmt='UIR', sep='\t')
  tune_data = reader.read(fpath=f"datasets/{dataset}/{dataset}_tune.txt", fmt='UIR', sep='\t')
  test_data = reader.read(fpath=f"datasets/{dataset}/{dataset}_test.txt", fmt='UIR', sep='\t')
  return train_data, tune_data, test_data

def load_data(train_data, test_data):
  eval_method = BaseMethod.from_splits(
      train_data=train_data, test_data=test_data, rating_threshold=1.0, exclude_unknowns=True, verbose=True
  )

  return eval_method

# running the cornac
def run_model(eval_method):


  models = [
            WMF(k=50, max_iter=50, learning_rate=0.001, lambda_u=0.01, lambda_v=0.01, verbose=True, seed=123),
            HPF(k=50, seed=123, hierarchical=False, name="PF"),
            VAECF(k=10, autoencoder_structure=[20], act_fn="tanh", likelihood="mult", n_epochs=100, batch_size=100, learning_rate=0.001, beta=1.0, seed=123, use_gpu=True, verbose=True),
          #  NeuMF(num_factors=9, layers=[32, 16, 8], act_fn="tanh", num_epochs=5, num_neg=3, batch_size=256, lr=0.001, seed=42, verbose=True)
            ]

  # define metrics to evaluate the models
  metrics = [
            AUC(), MAP(), MRR(), NDCG(k=10), Recall(k=10)
            ]

  # put it together in an experiment, voilà!
  exp = cornac.Experiment(eval_method=eval_method, models=models, metrics=metrics)
  exp.run()

  return exp

def read_user_groups(user_group_fpath: str, gid) -> set:

  user_group = open(user_group_fpath, 'r').readlines()
  user_ids = set()
  for eachline in user_group:
    uid = eachline.strip()
    # convert uids to uidx
    uid = eval_method.train_set.uid_map[uid]
    uid = int(uid)
    user_ids.add(uid)
    U[uid][gid] = 1
  return user_ids

# read test data
def read_ground_truth(test_file):

  ground_truth = defaultdict(set)
  truth_data = open(test_file, 'r').readlines()
  for eachline in truth_data:
    uid, iid, _ = eachline.strip().split()

    # convert uids to uidx
    uid = eval_method.train_set.uid_map[uid]
    # convert iids to iidx
    iid = eval_method.train_set.iid_map[iid]

    uid, iid = int(uid), int(iid)
    ground_truth[uid].add(iid)
  return ground_truth

# read train data
def read_train_data(train_file):

  train_checkins = defaultdict(set)
  pop_items = dict()
  train_data = open(train_file, 'r').readlines()

  for eachline in train_data:
    uid, iid, _ = eachline.strip().split()

    # convert uids to uidx
    uid = eval_method.train_set.uid_map[uid]
    # convert iids to iidx
    iid = eval_method.train_set.iid_map[iid]

    uid, iid = int(uid), int(iid)
    # a dictionary of popularity of items
    if iid in pop_items.keys():
      pop_items[iid] += 1
    else:
      pop_items[iid] = 1
    train_checkins[uid].add(iid)
  return train_checkins, pop_items

"""## Metrics"""

def catalog_coverage(predicted: list, catalog: list) -> float:

  predicted_flattened = [p for sublist in predicted for p in sublist]
  L_predictions = len(set(predicted_flattened))
  catalog_coverage = round(L_predictions / (len(catalog) * 1.0) * 100, 2)
  # output: precent (%)
  return catalog_coverage

def novelty(predicted: list, pop: dict, u: int, k: int) -> float:

  self_information = 0
  for item in predicted:
    if item in pop.keys():
      item_popularity = pop[item] / u
      item_novelty_value = np.sum(-np.log2(item_popularity))
    else:
      item_novelty_value = 0
    self_information += item_novelty_value
  novelty_score = self_information / k
  return novelty_score

def precisionk(actual, predicted):
  return 1.0 * len(set(actual) & set(predicted)) / len(predicted)

def recallk(actual, predicted):
  return 1.0 * len(set(actual) & set(predicted)) / len(actual)

def ndcgk(actual, predicted):
  idcg = 1.0
  dcg = 1.0 if predicted[0] in actual else 0.0
  for i, p in enumerate(predicted[1:]):
    if p in actual:
      dcg += 1.0 / np.log(i+2)
    idcg += 1.0 / np.log(i+2)
  return dcg / idcg

def load_ranking_matrices(model, total_users, total_items, topk):
  S = np.zeros((total_users, total_items))
  P = np.zeros((total_users, topk))

  # for model in exp.models:
  print(model.name)
  for uid in tqdm(range(total_users)):
    S[uid] = model.score(uid)
    P[uid] = np.array(list(reversed(model.score(uid).argsort()))[:topk])

  return S, P


def load_ground_truth_index(total_users, topk, P, train_checkins):
  Ahelp = np.zeros((total_users, topk))
  for uid in tqdm(range(total_users)):
    for j in range(topk):
      # convert user_ids to user_idx
      # convert item_ids to item_idx
      if P[uid][j] in train_checkins[uid]:
        Ahelp[uid][j] = 1
  return Ahelp

# create a set of IDs for each users group
def read_item_groups(item_group_fpath: str, gid) -> set:
  item_group = open(item_group_fpath, 'r').readlines()
  item_ids = set()
  for eachline in item_group:
    iid = eachline.strip()
    # convert iids to iidx
    iid = eval_method.train_set.iid_map[iid]
    iid = int(iid)
    item_ids.add(iid)
    I[iid][gid] = 1
  return item_ids

def read_item_index(total_users, topk, no_item_groups):
  Ihelp = np.zeros((total_users, topk, no_item_groups))
  for uid in range(total_users):
    for lid in range(topk):
      # convert item_ids to item_idx
      if P[uid][lid] in shorthead_item_ids:
        Ihelp[uid][lid][0] = 1
      elif P[uid][lid] in longtail_item_ids:
        Ihelp[uid][lid][1] = 1
  return Ihelp

"""## Evaluation"""

def metric_per_group(group, W):
  NDCG10 = list()
  Pre10 = list()
  Rec10 = list()
  Novelty10 = list()
  predicted = list()
  All_Predicted = list()

  for uid in tqdm(group):
    if uid in ground_truth.keys():
      for j in range(50):
        if W[uid][j].x == 1:
          predicted.append(P[uid][j])
      copy_predicted = predicted[:]
      All_Predicted.append(copy_predicted)
      NDCG = ndcgk(actual=ground_truth[uid], predicted=predicted)
      Pre = precisionk(actual=ground_truth[uid], predicted=predicted)
      Rec = recallk(actual=ground_truth[uid], predicted=predicted)
      Novelty = novelty(predicted=predicted, pop=pop_items, u=eval_method.total_users, k=10)

      NDCG10.append(NDCG)
      Pre10.append(Pre)
      Rec10.append(Rec)
      Novelty10.append(Novelty)

      # cleaning the predicted list for a new user
      predicted.clear()

  catalog = catalog_coverage(predicted=All_Predicted, catalog=pop_items.keys())
  return round(np.mean(NDCG10), 5), round(np.mean(Pre10), 5), round(np.mean(Rec10), 5), round(np.mean(Novelty10), 5), catalog

def metric_on_all(W):
  """
  """
  predicted_user = list()
  NDCG_all = list()
  PRE_all = list()
  REC_all = list()
  Novelty_all = list()
  All_Predicted = list()


  for uid in tqdm(range(eval_method.total_users)):
    if uid in ground_truth.keys():
      for j in range(50):
        if W[uid][j].x == 1:
          predicted_user.append(P[uid][j])

      copy_predicted = predicted_user[:]
      All_Predicted.append(copy_predicted)

      NDCG_user = ndcgk(actual=ground_truth[uid], predicted=predicted_user)
      PRE_user = precisionk(actual=ground_truth[uid], predicted=predicted_user)
      REC_user = recallk(actual=ground_truth[uid], predicted=predicted_user)
      Novelty_user = novelty(predicted=predicted_user, pop=pop_items, u=eval_method.total_users, k=10)

      NDCG_all.append(NDCG_user)
      PRE_all.append(PRE_user)
      REC_all.append(REC_user)
      Novelty_all.append(Novelty_user)

      # cleaning the predicted list for a new user
      predicted_user.clear()

  catalog = catalog_coverage(predicted=All_Predicted, catalog=pop_items.keys())
  return round(np.mean(NDCG_all), 5), round(np.mean(PRE_all), 5), round(np.mean(REC_all), 5), round(np.mean(Novelty_all), 5), catalog

def relevant_short_long_items(W):
  # list of recommended items to a user
  predicted_user = list()
  actual_user = []
  recommedned_item_groups = [0 , 0]
  for uid in tqdm(range(eval_method.total_users)):
    actual_recommedned = []
    if uid in ground_truth.keys():
      for j in range(50):
        if W[uid][j].x == 1:
          predicted_user.append(P[uid][j])
      actual_user = ground_truth[uid]
      actual_recommedned = set(actual_user) & set(predicted_user)
      predicted_user.clear()
      for actual_rec_item in actual_recommedned:
        if actual_rec_item in shorthead_item_ids:
          recommedned_item_groups[0] += 1
        elif actual_rec_item in longtail_item_ids:
          recommedned_item_groups[1] += 1
  # print(recommedned_item_groups)
  return recommedned_item_groups

"""## Fairness"""

def fairness_optimisation(fairness='N', uepsilon=0.000005, iepsilon = 0.0000005):
  print(f"Runing fairness optimisation on '{fairness}', {format(uepsilon, 'f')}, {format(iepsilon, 'f')}")
  # V1: No. of users
  # V2: No. of top items (topk)
  # V3: No. of user groups
  # V4: no. og item groups
  V1, V2, V3, V4 = set(range(eval_method.total_users)), set(range(topk)), set(range(no_user_groups)), set(range(no_item_groups))

  # initiate model
  model = Model()

  # W is a matrix (size: user * top items) to be learned by model
  #W = [[model.add_var(var_type=BINARY) for j in V2] for i in V1]
  W = [[model.add_var() for j in V2] for i in V1]
  user_dcg = [model.add_var() for i in V1]
  user_ndcg = [model.add_var() for i in V1]
  group_ndcg_v = [model.add_var() for k in V3]
  item_group = [model.add_var() for k in V4]

  user_precision=[model.add_var() for i in V1]
  group_precision=[model.add_var() for k in V3]

  user_recall=[model.add_var() for i in V1]
  group_recall= [model.add_var() for k in V3]

  if fairness == 'N':
    ### No Fairness ###
    model.objective = maximize(xsum((S[i][j] * W[i][j]) for i in V1 for j in V2))
  elif fairness == 'C':
    ### C-Fairness: NDCG_Best: group_ndcg_v[1] - group_ndcg_v[0] ###
    model.objective = maximize(xsum((S[i][j] * W[i][j]) for i in V1 for j in V2) - uepsilon * (group_ndcg_v[1] - group_ndcg_v[0]))
  elif fairness == 'P':
    model.objective = maximize(xsum((S[i][j] * W[i][j]) for i in V1 for j in V2) - iepsilon * (item_group[0] - item_group[1]))
  elif fairness == 'CP':
    model.objective = maximize(xsum((S[i][j] * W[i][j]) for i in V1 for j in V2) - uepsilon * (group_ndcg_v[1] - group_ndcg_v[0]) - iepsilon * (item_group[0] - item_group[1]))

  # first constraint: the number of 1 in W should be equal to top-k, recommending top-k best items
  k = 10
  for i in V1:
      model += xsum(W[i][j] for j in V2) == k

  for i in V1:
    user_idcg_i = 7.137938133620551

    model += user_dcg[i] == xsum((W[i][j] * Ahelp[i][j]) for j in V2)
    model += user_ndcg[i] == user_dcg[i] / user_idcg_i

    model += user_precision[i]==xsum((W[i][j] * Ahelp[i][j]) for j in V2) / k
    model += user_recall[i]==xsum((W[i][j] * Ahelp[i][j]) for j in V2) / len(train_checkins[i])

  for k in V3:
    model += group_ndcg_v[k] == xsum(user_dcg[i] * U[i][k] for i in V1)
    model += group_precision[k] == xsum(user_precision[i] * U[i][k] for i in V1)
    model += group_recall[k] == xsum(user_recall[i] * U[i][k] for i in V1)

  for k in V4:
    model += item_group[k] == xsum(W[i][j] * Ihelp[i][j][k] for i in V1 for j in V2)

  item_group_ids = [[], []]

  for i in V1:
    for j in V2:
      model += W[i][j] <= 1
  # optimizing
  model.optimize()

  return W, item_group

"""## Run"""

def write_results():
  ndcg_ac, pre_ac, rec_ac, novelty_ac, coverage_ac = metric_per_group(group=active_user_ids, W=W)
  ndcg_iac, pre_iac, rec_iac, novelty_iac, coverage_iac = metric_per_group(group=inactive_user_ids, W=W)
  ndcg_all, pre_all, rec_all, novelty_all, coverage_all = metric_on_all(W=W)
  rel_short_items, rel_long_items = relevant_short_long_items(W)
  if fair_mode == 'N':
    results.write(f"{dataset},{model.name},{u_group}%,{i_group}%,{fair_mode},-,-,{ndcg_all},{ndcg_ac},{ndcg_iac},{pre_all},{pre_ac},{pre_iac},{rec_all},{rec_ac},{rec_iac},{novelty_all},{novelty_ac},{novelty_iac},{coverage_all},{coverage_ac},{coverage_iac},{item_group[0].x},{rel_short_items},{item_group[1].x},{rel_long_items},{eval_method.total_users * 10}=={item_group[0].x + item_group[1].x}")
  elif fair_mode == 'C':
    results.write(f"{dataset},{model.name},{u_group}%,{i_group}%,{fair_mode},{format(user_eps, '.7f')},-,{ndcg_all},{ndcg_ac},{ndcg_iac},{pre_all},{pre_ac},{pre_iac},{rec_all},{rec_ac},{rec_iac},{novelty_all},{novelty_ac},{novelty_iac},{coverage_all},{coverage_ac},{coverage_iac},{item_group[0].x},{rel_short_items},{item_group[1].x},{rel_long_items},{eval_method.total_users * 10}=={item_group[0].x + item_group[1].x}")
  elif fair_mode == 'P':
    results.write(f"{dataset},{model.name},{u_group}%,{i_group}%,{fair_mode},-,{format(item_eps, '.7f')},{ndcg_all},{ndcg_ac},{ndcg_iac},{pre_all},{pre_ac},{pre_iac},{rec_all},{rec_ac},{rec_iac},{novelty_all},{novelty_ac},{novelty_iac},{coverage_all},{coverage_ac},{coverage_iac},{item_group[0].x},{rel_short_items},{item_group[1].x},{rel_long_items},{eval_method.total_users * 10}=={item_group[0].x + item_group[1].x}")
  elif fair_mode == 'CP':
    results.write(f"{dataset},{model.name},{u_group}%,{i_group}%,{fair_mode},{format(user_eps, '.7f')},{format(item_eps, '.7f')},{ndcg_all},{ndcg_ac},{ndcg_iac},{pre_all},{pre_ac},{pre_iac},{rec_all},{rec_ac},{rec_iac},{novelty_all},{novelty_ac},{novelty_iac},{coverage_all},{coverage_ac},{coverage_iac},{item_group[0].x},{rel_short_items},{item_group[1].x},{rel_long_items},{eval_method.total_users * 10}=={item_group[0].x + item_group[1].x}")
  results.write('\n')

# 1: Iterate over the datasets
for dataset in ds_names:
  print(f"Datasets: {dataset}")
  # read train, tune, test datasets
  train_data, tune_data, test_data = read_data(dataset=dataset)
  # load data into Cornac and create eval_method
  eval_method = load_data(train_data=train_data, test_data=test_data)
  total_users = eval_method.total_users
  total_items = eval_method.total_items
  # load train_checkins and pop_items dictionary
  train_checkins, pop_items = read_train_data(train_file = f"datasets/{dataset}/{dataset}_train.txt")
  # load ground truth dict
  ground_truth = read_ground_truth(test_file = f"datasets/{dataset}/{dataset}_test.txt")
  # run Cornac models and create experiment object including models' results
  exp = run_model(eval_method=eval_method)
  # 4: read user groups
  for u_group in ds_users:
    # read matrix U for users and their groups
    U = np.zeros((total_users, no_user_groups))
    # load active and inactive users
    active_user_ids = read_user_groups(user_group_fpath = f"user_groups/{dataset}/{u_group}/active_ids.txt", gid = 0)
    inactive_user_ids = read_user_groups(user_group_fpath = f"user_groups/{dataset}/{u_group}/inactive_ids.txt", gid = 1)
    print(f"ActiveU: {len(active_user_ids)}, InActive: {len(inactive_user_ids)}, All: {len(active_user_ids) + len(inactive_user_ids)}")
    len_sizes = [len(active_user_ids), len(inactive_user_ids)]
    # 5: read item groups
    for i_group in ds_items:
      # read matrix I for items and their groups
      I = np.zeros((total_items, no_item_groups))
      # read item groups
      shorthead_item_ids = read_item_groups(item_group_fpath = f"item_groups/{dataset}/{i_group}/shorthead_items.txt", gid = 0)
      longtail_item_ids = read_item_groups(item_group_fpath = f"item_groups/{dataset}/{i_group}/longtail_items.txt", gid = 1)
      print(f"No. of Shorthead Items: {len(shorthead_item_ids)} and No. of Longtaill Items: {len(longtail_item_ids)}")
      # 2: iterate over the models
      for model in exp.models:
        results = open(f"results/results_{dataset}_{model.name}.csv", 'w')
        results.write("Dataset,Model,GUser,GItem,Type,User_EPS,Item_EPS,ndcg_ALL,ndcg_ACT,ndcg_INACT,Pre_ALL,Pre_ACT,Pre_INACT,Rec_ALL,Rec_ACT,Rec_INACT,Nov_ALL,Nov_ACT,Nov_INACT,Cov_ALL,Cov_ACT,Cov_INACT,Short_Items,Rel_Short,Long_Items,Rel_Long,All_Items\n")
        print(f"> Model: {model.name}")
        # load matrix S and P
        S, P = load_ranking_matrices(model=model, total_users=total_users, total_items=total_items, topk=topk)
        # load matrix Ahelp
        Ahelp = load_ground_truth_index(total_users=total_users, topk=topk, P=P, train_checkins=train_checkins)
        # load matrix Ihelp
        Ihelp = read_item_index(total_users=total_users, topk=50, no_item_groups=no_item_groups)
        # iterate on fairness mode: user, item, user-item
        for fair_mode in ['N', 'C', 'P', 'CP']:
          if fair_mode == 'N':
            W, item_group = fairness_optimisation(fairness=fair_mode)
            write_results()
          elif fair_mode == 'C':
            for user_eps in [0.005, 0.01, 0.03, 0.05, 0.07, 0.09, 0.5, 1.0]:
              W, item_group = fairness_optimisation(fairness=fair_mode, uepsilon=user_eps)
              write_results()
          elif fair_mode == 'P':
            for item_eps in [0.005, 0.01, 0.03, 0.05, 0.07, 0.09, 0.5, 1.0]:
              W, item_group = fairness_optimisation(fairness=fair_mode, iepsilon=item_eps)
              write_results()
          elif fair_mode == 'CP':
            for user_eps in [0.005, 0.01, 0.03, 0.05, 0.07, 0.09, 0.5, 1.0]:
              for item_eps in [0.005, 0.01, 0.03, 0.05, 0.07, 0.09, 0.5, 1.0]:
                W, item_group = fairness_optimisation(fairness=fair_mode, uepsilon=user_eps, iepsilon=item_eps)
                write_results()
        results.close()


