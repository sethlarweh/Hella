import flask
from flask import Flask, jsonify, request, render_template
import os
import sys
sys.path.append("../ml")
from anomaly_model import AnomalyModel
sys.path.append("../monitor")
import test_data
import pickle
from scapy.all import *

dataset_dir = 'datasets/'
model_dir = 'models/'

app = Flask(__name__)

@app.route('/')
def index():
	# Take all files in the appropriate directories matching ".pkl"
	dataset_names = [(make_name_pretty(name), name) for name in os.listdir(dataset_dir) if name.endswith('.pkl')]
	model_names = [(make_name_pretty(name), name) for name in os.listdir(model_dir) if name.endswith('.pkl')]
	return render_template('index.html', dataset_names=dataset_names, model_names=model_names)

@app.route('/predict', methods=['POST'])
def predict():
	params = request.get_json(silent=True, force=True)
	print(params)
	model_path = model_dir + params['model']
	dataset_path = dataset_dir + params['dataset']

	model = AnomalyModel()
	model.load(model_path)

	with open(dataset_path, 'r') as f:
		test_data = pickle.load(f)

	fr = getattr(feat_module, model.featurizer)()

	X = [fr.featurize(Ether(dp.pkt[1])) for dp in test_data.dps]
	print(len(X))
	Y = [1 if dp.malicious else 0 for dp in test_data.dps]

	start = time.time()
	pred = model.predicts(X)
	diff = time.time() - start
	df = model.model.decision_function(X) 


	metrics = model.validation(pred, Y)
	Y_prime = [-1 if y == 1 else 1 for y in Y]
	roc_auc = model.roc_curve(df, Y_prime)
	info = {}
	info['metrics'] = metrics
	info['roc_auc'] = roc_auc
	info['time'] = diff
	print(info)

	return jsonify(info)

# Take a model/dataset name and "prettify" it
# by replacing underscores with spaces and using titlecase
def make_name_pretty(name):
	name = name[:-4]
	name = name.replace("_", " ")
	name = name.title()
	return name

if __name__ == '__main__':
	feat_module = __import__('featurizer')
	app.run(host='0.0.0.0', port=8000, debug=True)