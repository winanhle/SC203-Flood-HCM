# SC203 — Berlin to HCMC flood experiments

Archive of all ten notebook uploads received on 3 November 2026 (five notebooks plus five reuploads), and the executed HCMC Method 2 experiment.

- `berlin/`: original supplied notebooks with saved outputs.
- `berlin/reuploads/`: repeated uploads, retained with original filenames.
- `hcm/HCMC_Method2_RF.ipynb`: executed Random Forest adaptation.
- `hcm/results/`: data audit, grouped metrics and predictions.
- `hcm/README.md`: methodology, limitations, attribution and run instructions.
- `deliverables/`: complete HCMC experiment ZIP.

HCMC uses 147 available upper-depth endpoints. Event/source grouped RF MAE: 0.2893 m; mean baseline: 0.2611 m. Execution succeeds, but independent-event predictive usefulness is not established. New RF models were trained on HCMC; Berlin weights were not transferred. This run used local Python, not Kaggle.

Large Berlin rasters and model checkpoints were not attached. The supplied notebooks reference https://www.kaggle.com/datasets/longltrnhong/berlin-sa1-prepared and https://www.kaggle.com/datasets/longltrnhong/berlin-phase4-unet-results .

## Sources

- HCMC: Hardy & Radziute (2026), https://doi.org/10.23708/8Y16HU , CC BY-NC 4.0.
- Berlin code: https://github.com/omarseleem92/Machine_learning_for_urban_flooding
- Berlin data supplied link: https://zenodo.org/records/7516408 ; notebooks use https://zenodo.org/records/7221058 .
- Paper: https://doi.org/10.5194/nhess-23-809-2023 .

The HCMC adaptation and documentation were prepared with ChatGPT; metrics are from executed code. Third-party materials retain their own license terms.
