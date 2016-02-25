# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from weboob.tools.test import BackendTest
import itertools


class SevenFiftyGramsTest(BackendTest):
    MODULE = '750g'

    def test_recipe(self):
        recipes = list(itertools.islice(self.backend.iter_recipes('fondue'), 0, 20))
        for recipe in recipes:
            full_recipe = self.backend.get_recipe(recipe.id)
            self.assertTrue(full_recipe.instructions, 'No instructions for %s' % recipe.id)
            self.assertTrue(full_recipe.ingredients, 'No ingredients for %s' % recipe.id)
            self.assertTrue(full_recipe.title, 'No title for %s' % recipe.id)
            self.assertTrue(full_recipe.preparation_time, 'No preparation time for %s' % recipe.id)
