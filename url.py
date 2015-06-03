import os.path
import re
import sys
import time
import urllib2
import grid


# --- MAIN CODE BEGINS HERE ---
print ""

# System argument gives the puzzle ID, if none revert to a default
puzzle_id = 139714
if len(sys.argv) > 1:
   puzzle_id = int(sys.argv[1])
base_file_name = 'puzzles/griddler_%d' % puzzle_id

# Pull in the puzzle's solver page. This is the one that has the puzzle definition.
# If already exists on disk, just use that one. Otherwise grab from website and save to disk.

disk_file_name = base_file_name + '.html'
web_html = ""
if os.path.isfile(disk_file_name):
   print "Reading HTML from disk."
   f = open(disk_file_name, 'r')
   web_html = f.read()
   f.close()
else:
   print "Reading HTML from website."
   web_url_base = 'http://www.griddlers.net/griddlers?p_p_id=griddlers_WAR_puzzles&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=html&p_p_cacheability=cacheLevelPage&p_p_col_id=column-2&p_p_col_count=1&_griddlers_WAR_puzzles_id={0}&_griddlers_WAR_puzzles_view=detail'
   web_url = web_url_base.format(puzzle_id) # Add the puzzle ID into the url
   web_file = urllib2.urlopen(web_url)
   web_html = web_file.read()
   
   print "Writing HTML to disk."
   f = open(disk_file_name, 'w')
   f.write(web_html)
   f.close()
print "Page data retrieved."


# Extract puzzle details

# Puzzle width
result = re.search('var pwidth = ([0-9]+)', web_html)
puzz_width = int(result.group(1))
print "Puzzle width:", puzz_width

# Puzzle height
result = re.search('var pheight = ([0-9]+)', web_html)
puzz_height = int(result.group(1))
print "Puzzle height:", puzz_height

# Puzzle horizontal (left) codes
puzz_left_hints = []
for result in re.finditer('leftCodes\[[0-9]+\]=\"(.*)\";', web_html): # todo: better regex use, can probably do this in one line
   left_hint_list = []
   for r in result.group(1).split(','):
      left_hint = re.search('([0-9]+):([0-9]+)', r)
      if left_hint:
         palette_id = int(left_hint.group(1))
         count = int(left_hint.group(2))
         left_hint_list.append( (palette_id, count) )
   puzz_left_hints.append(left_hint_list)

# Puzzle vertical (top) codes
puzz_top_hints = []
for result in re.finditer('topCodes\[[0-9]+\]=\"(.*)\";', web_html):
   top_hint_list = []
   for r in result.group(1).split(','):
      top_hint = re.search('([0-9]+):([0-9]+)', r)
      if top_hint:
         palette_id = int(top_hint.group(1))
         count = int(top_hint.group(2))
         top_hint_list.append( (palette_id, count) )
   puzz_top_hints.append(top_hint_list)

print "Column hints:"
print '\n'.join([str(hint) for hint in puzz_top_hints]) # todo: try to use map for this?
print "\n"

print "Row hints:"
print '\n'.join([str(hint) for hint in puzz_left_hints])
print "\n"

puzz_grid = grid.Grid(puzz_width, puzz_height, puzz_top_hints, puzz_left_hints)

# Create puzzle grid
#last_puzz_grid = copy_grid(puzz_grid)

# Search possibilities
begin_time = time.clock()
puzz_grid.solve()
end_time = time.clock()
solve_time = end_time - begin_time

# We're done solving! Now get the solve time and dump data to disk.
solve_h = int(solve_time / 60 / 60)
solve_m = int((solve_time - (solve_h * 60 * 60)) / 60)
solve_s = int(solve_time - (solve_m * 60))
solve_time_str = 'Solve time: {0} ({1}h {2}m {3}s)'.format(solve_time, solve_h, solve_m, solve_s)

print 'Final grid:'
print puzz_grid
print solve_time_str

# todo: use YAML
result_file_name = base_file_name + '.txt'
with open(result_file_name, 'w') as fout:
   fout.write(solve_time_str + '\n')
   fout.write(str(puzz_grid))
#raw_input("Press Enter to continue...")

# - Could have a speedup where if the row is empty and the sum of the components isn't long enough,
#   just skip the row and return all empties. I already have this but the speedup I have might be faulty.
# - Create a queueing system for which rows / cols to look through. Initially add one or more that are
#   very long. Then when a cell changes, add that row or col to the queue to be checked. If the queue is
#   empty then revert to scanning through row x col.
# - GRAPHICS!!
# - Maybe there's a way to start the hints / expansions at a certain point, based on what's already out?
#   I guess if you knew everything starting from the left or right you could say definitively whole hints.
# - Could investigate using regex matching algorithms to match hints with rows.